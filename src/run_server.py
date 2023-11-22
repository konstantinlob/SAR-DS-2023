from stuff import Address

def run_server(is_primary: bool = True, host: str = "127.0.0.1", port: int = 5000, primary_at: Address = None):
    from server import PrimaryServer, BackupServer
    from stuff import Address
    from flask import Flask, request

    app = Flask(__name__)
    if is_primary:
        server = PrimaryServer(Address(host, port))

        @app.post("/replication/init-backup")
        def replication_init_backup():
            return server.handle_replication_init_backup(request)
    else:
        server = BackupServer(Address(host, port), primary_server=primary_at)

    @app.post("/client/init")
    def init_client():
        return server.handle_client_init(request)

    @app.post("/client/authenticate")
    def authenticate_client():
        return server.handle_client_authenticate(request)

    @app.post("/client/demo-message")
    def demo_message():
        return server.handle_client_demo_message(request)

    app.run(host=host, port=port, debug=True)
