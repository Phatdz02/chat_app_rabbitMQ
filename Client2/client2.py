import pika
import tkinter as tk
from threading import Thread
from tkinter import filedialog
from PIL import Image, ImageTk
import base64
import os
import io

contMensagensEnviadas = 0
user = None

def update_chat_window(message, image=None):
    chat_window.config(state=tk.NORMAL)
    chat_window.insert(tk.END, message + '\n')
    if image:
        chat_window.image_create(tk.END, image=image)
        chat_window.insert(tk.END, '\n')
    chat_window.config(state=tk.DISABLED)
    chat_window.see(tk.END)

def save_to_history(user, message, image_path=None):
    try:
        with open("History.txt", "a", encoding="utf-8") as history_file:
            if image_path:
                history_file.write(f"{user}: [image] {image_path}\n")
            else:
                history_file.write(f"{user}: {message}\n")
    except Exception as e:
        print(f"Error saving to history: {e}")

def send_message():
    global contMensagensEnviadas
    contMensagensEnviadas += 1
    message = message_entry.get("1.0", tk.END).strip()
    if message:
        mensagem = f"{message}>>{contMensagensEnviadas}>>{user}"
        channelEnvioMensagens.basic_publish(exchange='chat', routing_key='', body=mensagem)
        update_chat_window(f"{user}: {message}")
        save_to_history(user, message)
        message_entry.delete("1.0", tk.END)

def send_image():
    global contMensagensEnviadas
    contMensagensEnviadas += 1
    image_path = filedialog.askopenfilename()
    if image_path:
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        filename = os.path.basename(image_path)
        mensagem = f"[image]>>{contMensagensEnviadas}>>{user}>>{filename}>>{image_data}"
        channelEnvioMensagens.basic_publish(exchange='chat', routing_key='', body=mensagem)
        img = Image.open(image_path)
        img.thumbnail((100, 100))
        img = ImageTk.PhotoImage(img)
        update_chat_window(f"{user}: [image]", img)

        image_save_path = os.path.join('Client1/image', filename)
        if not os.path.exists('Client1/image'):
            os.makedirs('Client1/image')
        save_to_history(user, "[image]", image_save_path)
        with open(image_save_path, "wb") as f:
            f.write(base64.b64decode(image_data))

def repost_callback(ch, method, properties, body):
    try:
        message_parts = body.decode().split(">>", 4)
        if message_parts[2] != user:  # Ignore messages sent by self
            if message_parts[0] == "[image]":
                filename = message_parts[3]
                image_data = base64.b64decode(message_parts[4])
                image_save_path = os.path.join('image', filename)
                if not os.path.exists('image'):
                    os.makedirs('image')
                with open(image_save_path, "wb") as f:
                    f.write(image_data)
                image = Image.open(io.BytesIO(image_data))
                image.thumbnail((100, 100))
                image = ImageTk.PhotoImage(image)
                display_messenger_receive(message_parts[2], "[image]", image)
            else:
                display_messenger_receive(message_parts[2], message_parts[0])
    except Exception as e:
        print(f"Error handling received message: {str(e)}")

def display_messenger_receive(user, message, image=None):
    formatted_message = f"{user}: {message}"
    update_chat_window(formatted_message, image)
    save_to_history(user, message)

def start_consuming():
    try:
        channelRecebimentoMensagens.start_consuming()
    except Exception as e:
        print(f"Error in consuming messages: {e}")

def start_session():
    try:
        with open("History.txt", "a", encoding="utf-8") as history_file:
            history_file.write("{\n")
    except Exception as e:
        print(f"Error starting session: {e}")

def end_session():
    try:
        with open("History.txt", "a", encoding="utf-8") as history_file:
            history_file.write("}\n")
    except Exception as e:
        print(f"Error ending session: {e}")

def initialize_client():
    global user
    user = username_entry.get()
    if user:
        if not os.path.exists('image'):
            os.makedirs('image')
        app.deiconify()
        username_window.destroy()

try:
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channelEnvioMensagens = connection.channel()
    channelEnvioMensagens.exchange_declare(exchange='chat', exchange_type='fanout')

    channelRecebimentoMensagens = connection.channel()
    channelRecebimentoMensagens.exchange_declare(exchange='chat', exchange_type='fanout')
    result = channelRecebimentoMensagens.queue_declare('', exclusive=True)
    queue_name = result.method.queue
    channelRecebimentoMensagens.queue_bind(exchange='chat', queue=queue_name)
    channelRecebimentoMensagens.basic_consume(queue=queue_name, on_message_callback=repost_callback, auto_ack=True)
except Exception as e:
    print(f"Error connecting to RabbitMQ: {e}")

app = tk.Tk()
app.withdraw()

username_window = tk.Toplevel()
username_window.title("Nhập tên người dùng")

username_label = tk.Label(username_window, text="Nhập tên người dùng:")
username_label.pack()

username_entry = tk.Entry(username_window)
username_entry.pack()

username_button = tk.Button(username_window, text="OK", command=initialize_client)
username_button.pack()

app.title("RabbitMQ Client 2")

chat_window = tk.Text(app, height=20, width=50, state=tk.DISABLED)
chat_window.pack()

message_entry = tk.Text(app, height=2, width=50)
message_entry.pack()

send_button = tk.Button(app, text="Gửi Tin Nhắn", command=send_message)
send_button.pack()

send_image_button = tk.Button(app, text="Gửi Ảnh", command=send_image)
send_image_button.pack()

consuming_thread = Thread(target=start_consuming)
consuming_thread.start()

app.protocol("WM_DELETE_WINDOW", lambda: (end_session(), app.destroy()))
start_session()

app.mainloop()
