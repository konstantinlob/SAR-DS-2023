from run_server import *

run_server(is_primary=False, port=5001, primary_at=Address("127.0.0.1", 5000))
