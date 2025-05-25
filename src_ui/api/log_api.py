from flask import Blueprint, Response
import time, json, queue

log_bp = Blueprint('log', __name__)
log_queue = queue.Queue()

@log_bp.route('/api/log-stream')
def log_stream():
    def generate():
        yield "data: {\"message\": \"连接已建立，等待日志...\"}\n\n"
        while True:
            try:
                message = log_queue.get(block=False)
                if message:
                    yield f"data: {json.dumps({'message': message})}\n\n"
            except queue.Empty:
                yield "data: {\"keepalive\": true}\n\n"
            time.sleep(0.1)
    return Response(generate(), mimetype="text/event-stream") 