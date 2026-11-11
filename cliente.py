
import socket
import threading
import json

# Configuracion del servidor
HOST = "127.0.0.1"
PORT = 5000


# Recibir mensajes del servidor
def recibir_mensajes(cliente, detener):

    archivo = cliente.makefile(
        "r",
        encoding="utf-8"
    )

    try:

        for mensaje in archivo:

            print("\n" + mensaje.strip())
            print("> ", end="", flush=True)

    except OSError:

        pass

    finally:

        detener.set()
        archivo.close()


# Iniciar cliente
def iniciar_cliente():

    cliente = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    try:

        cliente.connect((HOST, PORT))

        # Solicitar credenciales
        usuario = input("Usuario: ")
        contrasena = input("Contrasena: ")

        credenciales = {
            "usuario": usuario,
            "contrasena": contrasena
        }

        # Enviar credenciales al servidor
        cliente.sendall(
            (json.dumps(credenciales) + "\n").encode("utf-8")
        )

        # Esperar respuesta de autenticacion
        archivo = cliente.makefile(
            "r",
            encoding="utf-8"
        )

        respuesta = archivo.readline()

        print(respuesta.strip())

        if not respuesta.startswith("OK:"):

            archivo.close()
            return

        # Crear hilo para recibir mensajes
        detener = threading.Event()

        hilo = threading.Thread(
            target=recibir_mensajes,
            args=(cliente, detener),
            daemon=True
        )

        hilo.start()

        print("\nChat iniciado")
        print("Comandos disponibles:")
        print("/repos usuario")
        print("/followers usuario")
        print("/hora")
        print("/todos mensaje")
        print("/usuarios")
        print("/adios")

        # Enviar mensajes
        while not detener.is_set():

            try:

                mensaje = input("> ")

            except (EOFError, KeyboardInterrupt):

                mensaje = "/adios"

            if not mensaje.strip():
                continue

            cliente.sendall(
                (mensaje + "\n").encode("utf-8")
            )

            if mensaje.lower() == "/adios":
                break

        detener.set()

    except ConnectionRefusedError:

        print("No se pudo conectar al servidor")

    except OSError as error:

        print("Error:", error)

    finally:

        cliente.close()
        print("Cliente desconectado")


if __name__ == "__main__":

    iniciar_cliente()
