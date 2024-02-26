import asyncio, logging, queue
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

import cv2

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

logger = logging.getLogger("uvicorn")

UDPSRC_PIPELINE = 'udpsrc port=9999 ! application/x-rtp,encoding-name=JPEG,payload=26 ! queue ! rtpjpegdepay ! jpegparse ! appsink drop=1'

client_queues = queue.deque()

templates = Jinja2Templates(directory="templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    cap = cv2.VideoCapture()
    asyncio.get_running_loop().run_in_executor(None, consume_pipeline, cap)
    yield
    cap.release()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


def consume_pipeline(cap):
    cap.open(UDPSRC_PIPELINE, cv2.CAP_GSTREAMER)
    cap.set(cv2.CAP_PROP_FORMAT, -1)

    try:
        while (cap.isOpened()):
            ret, frame = cap.read()

            if not ret:
                break

            qframe = b'--kwali\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(frame) + b'\r\n'

            for q in client_queues:
                q.put_nowait(qframe)
    finally:
        cap.release()


async def get_frame(client_queue):
    while True:
        yield await client_queue.get()


async def close_client(client_queue):
    logger.info(f'Current # of clients: {len(client_queues)}')
    client_queues.remove(client_queue)
    logger.info(f'Current # of clients: {len(client_queues)}')


@app.get('/mjpeg_stream')
async def stream(background_tasks: BackgroundTasks):
    q = asyncio.Queue()
    client_queues.append(q)
    background_tasks.add_task(close_client, q)
    return StreamingResponse(get_frame(q), media_type='multipart/x-mixed-replace;boundary=kwali')


@app.get("/", response_class=HTMLResponse)
async def main(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")
