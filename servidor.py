
import socket
import threading
import json
import mysql.connector
import requests
from datetime import datetime

HOST = "127.0.0.1"
PORT = 5000

clientes = {}
lock = threading.Lock()


def conectar_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="login"
    )


def crear_tablas():
    conexion = conectar_db()
    cursor = conexion.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repositorios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            usuario VARCHAR(100),
            nombre VARCHAR(255),
            url TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS followers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            usuario VARCHAR(100),
            follower VARCHAR(100),
            url TEXT
        )
    """)

    conexion.commit()
    cursor.close()
    conexion.close()


def validar_usuario(usuario, contrasena):
    conexion = conectar_db()
    cursor = conexion.cursor()

    cursor.execute(
        "SELECT * FROM usuarios WHERE usuario = %s AND contrasena = %s",
        (usuario, contrasena)
    )

    resultado = cursor.fetchone()

    cursor.close()
    conexion.close()

    return resultado is not None

def enviar_a_todos(mensaje):
    with lock:
        conexiones = list(clientes.keys())

    for conexion in conexiones:
        try:
            conexion.sendall((mensaje + "\n").encode("utf-8"))
        except OSError:
            pass

def obtener_usuarios():
    with lock:
        lista = list(clientes.values())

    return ", ".join(lista) if lista else "No hay usuarios conectados"

def obtener_repositorios(usuario):
    respuesta = requests.get(
        f"https://api.github.com/users/cambonprofe/repos",
        params={"per_page": 100},
        timeout=15
    )

    if respuesta.status_code == 404:
        return "Usuario de GitHub inexistente"

    respuesta.raise_for_status()
    repositorios = respuesta.json()

    conexion = conectar_db()
    cursor = conexion.cursor()

    for repo in repositorios:
        cursor.execute("""
            INSERT INTO repositorios (usuario, nombre, url)
            VALUES (%s, %s, %s)
        """, (
            usuario,
            repo["name"],
            repo["html_url"]
        ))

    conexion.commit()
    cursor.close()
    conexion.close()

    return f"Se guardaron {len(repositorios)} repositorios"

def obtener_followers(usuario):
    respuesta = requests.get(
        f"https://api.github.com/users/cambonprofe/followers",
        params={"per_page": 100},
        timeout=15
    )

    if respuesta.status_code == 404:
        return "Usuario de GitHub inexistente"

    respuesta.raise_for_status()
    followers = respuesta.json()

    conexion = conectar_db()
    cursor = conexion.cursor()

    for follower in followers:
        cursor.execute("""
            INSERT INTO followers (usuario, follower, url)
            VALUES (%s, %s, %s)
        """, (
            usuario,
            follower["login"],
            follower["html_url"]
        ))

    conexion.commit()
    cursor.close()
    conexion.close()

    return f"Se guardaron {len(followers)} followers"

def procesar_comando(cliente, usuario, mensaje):

    partes = mensaje.split(maxsplit=1)
    comando = partes[0].lower()

    if comando == "/hora":

        return datetime.now().strftime("%H:%M:%S")

    elif comando == "/usuarios":

        return obtener_usuarios()

    elif comando == "/repos":

        if len(partes) < 2:
            return "Uso: /repos usuario"

        try:
            return obtener_repositorios(partes[1])
        except Exception as error:
            return f"Error: {error}"

    elif comando == "/followers":

        if len(partes) < 2:
            return "Uso: /followers usuario"

        try:
            return obtener_followers(partes[1])
        except Exception as error:
            return f"Error: {error}"

    elif comando == "/todos":

        if len(partes) < 2:
            return "Uso: /todos mensaje"

        enviar_a_todos(
            f"[{usuario}]: {partes[1]}"
        )

        return "Mensaje enviado a todos"

    elif comando == "/adios":

        return None

    else:

        return "Comando desconocido"

def atender_cliente(cliente, direccion):

    usuario = None

    try:

        archivo = cliente.makefile(
            "r",
            encoding="utf-8"
        )

        datos = archivo.readline()

        if not datos:
            return

        credenciales = json.loads(datos)

        usuario_ingresado = credenciales["usuario"]
        contrasena = credenciales["contrasena"]

        if not validar_usuario(usuario_ingresado, contrasena):

            cliente.sendall(
                b"ERROR: usuario o contrasena incorrectos\n"
            )

            return

        usuario = usuario_ingresado

        with lock:
            clientes[cliente] = usuario

        cliente.sendall(
            f"OK: Bienvenido {usuario}\n".encode("utf-8")
        )

        enviar_a_todos(
            f"[Servidor]: {usuario} se conecto"
        )

        print(f"{usuario} conectado desde {direccion}")

        for linea in archivo:

            mensaje = linea.strip()

            if not mensaje:
                continue

            if mensaje.startswith("/"):

                respuesta = procesar_comando(
                    cliente,
                    usuario,
                    mensaje
                )

                if respuesta is None:
                    cliente.sendall(
                        b"Adios. Sesion cerrada.\n"
                    )
                    break

                cliente.sendall(
                    (respuesta + "\n").encode("utf-8")
                )

            else:

                print(f"{usuario}: {mensaje}")

                cliente.sendall(
                    f"[Servidor recibio]: {mensaje}\n".encode("utf-8")
                )

    except Exception as error:

        print("Error:", error)

    finally:

        with lock:
            clientes.pop(cliente, None)

        cliente.close()

        if usuario:
            print(f"{usuario} desconectado")

            enviar_a_todos(
                f"[Servidor]: {usuario} se desconecto"
            )


def consola_servidor():

    while True:

        mensaje = input()

        if mensaje.strip():

            enviar_a_todos(
                f"[Servidor]: {mensaje}"
            )


def iniciar_servidor():

    crear_tablas()

    servidor = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    servidor.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    servidor.bind((HOST, PORT))
    servidor.listen()

    print("Servidor iniciado")
    print(f"Escuchando en {HOST}:{PORT}")

    hilo_consola = threading.Thread(
        target=consola_servidor,
        daemon=True
    )

    hilo_consola.start()

    while True:

        cliente, direccion = servidor.accept()

        hilo = threading.Thread(
            target=atender_cliente,
            args=(cliente, direccion)
        )

        hilo.start()


if __name__ == "__main__":

    iniciar_servidor()
