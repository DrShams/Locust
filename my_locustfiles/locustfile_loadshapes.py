from locust import HttpUser, TaskSet, task, events, tag, constant_pacing, run_single_user, LoadTestShape
import sys, os
from locust_influxdb_listener import InfluxDBListener, InfluxDBSettings
import yaml
import platform

#Определим что мы либо запустили тест в режиме дебага или нет
DEBUG_MODE = __name__ == "__main__"

# ===================
# Load config
# ===================
config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

GRPC_HOST = config['server_grpc']['host']
GRPC_PORT = config['server_grpc']['port']

REST_HOST = config['server_rest']['host']
REST_PORT = config['server_rest']['port']

INFLUX_HOST = config['influxdb']['host']
INFLUX_PORT = config['influxdb']['port']

grpc_folder = 'None'
if platform.system() == "Windows":
    grpc_folder = r"D:\GitHub\gRPC"
else:  # Linux, macOS, etc.
    grpc_folder = "/mnt/protos/"
print(f"Current grpc_folder {grpc_folder}")
sys.path.append(grpc_folder)

import helloworld_pb2
import helloworld_pb2_grpc

# ===================
# TaskSets
# ===================

import time, random, functools

def dynamic_pacing(min_delay, max_delay):
    """
    Decorator that enforces dynamic constant pacing.
    Ensures each task iteration (including execution time)
    lasts between min_delay and max_delay seconds.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            target = random.uniform(min_delay, max_delay)
            sleep_time = max(0, target - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
            return result
        return wrapper
    return decorator


@events.init.add_listener
def on_locust_init(environment, **_kwargs):
    """
    Hook event that enables starting an influxdb connection
    """
    # this settings matches the given docker-compose file
    if DEBUG_MODE:
        print("DEBUG mode: Skipping InfluxDBListener initialization")
        return
    influxDBSettings = InfluxDBSettings(
        host = INFLUX_HOST,#localhost
        port = INFLUX_PORT,
        influx_host=INFLUX_HOST,#localhost
        influx_port=INFLUX_PORT,
        user = 'myusername',
        pwd = 'passwordpasswordpassword',
        database = 'influxDatabase',
        interval_ms=1000
    )
    # start listerner with the given configuration
    InfluxDBListener(env=environment, influxDbSettings=influxDBSettings)
    print(f"InfluxDBListener host: {influxDBSettings.host}")

class PostTasks(TaskSet):
    wait_time = constant_pacing(1)

    @task
    @tag('posts')
    #@dynamic_pacing(2, 8)
    def view_posts(self):
        with self.client.post("/posts/1/", name="/posts/1",
                         json={"title": "Ruslan", "body": "bar", "userId": "1"},
                         catch_response=True) as resp:
            if resp.status_code != 201:
                resp.failure(f"Unexpected status: {resp.status_code}")
            else:
                resp.success()
        #if DEBUG_MODE:
        #    self.interrupt()
        #    exit(1)
    @task
    def stop(self):
        self.interrupt()

class PostTasksAnother(TaskSet):
    #wait_time = constant_pacing(5)
    # def wait_time(self):
    #     # случайный pacing от 3 до 8 секунд
    #     target_pacing = random.uniform(3, 7)
    #     # "constant pacing" эквивалент вручную
    #     last_run = getattr(self, "_last_run", 0)
    #     elapsed = time.time() - last_run
    #     self._last_run = time.time()
    #     return max(0, target_pacing - elapsed)

    @task
    @tag('posts')
    @dynamic_pacing(2, 8)
    def view_posts(self):
        #start_time = time.time()
        with self.client.post("/posts/2/", name="/posts/2",
                         json={"title": "Ruslan", "body": "bar", "userId": "1"},
                         catch_response=True) as resp:
            if resp.status_code != 201:
                resp.failure(f"Unexpected status: {resp.status_code}")
            else:
                resp.success()

        # --- pacing logic (dynamic constant pacing) ---
        # target_pacing = random.uniform(2, 8)
        # elapsed = time.time() - start_time
        # sleep_time = max(0, target_pacing - elapsed)
        # if sleep_time > 0:
        #     time.sleep(sleep_time)
    @task
    def stop(self):
        self.interrupt()
# ===================
# Основные пользователи
# ===================

class WebUserA(HttpUser):
    host = f"http://{REST_HOST}:{REST_PORT}"
    tasks = {PostTasks: 1}  # весами регулируем вероятность

    def on_start(self):
        response = self.client.post("/login/", name="/userlogin",
                         json={"username": "alice", "password": "123"}
                         )
        self.session_id = response.json().get("session_id")
    def on_stop(self):
        headers = {"Authorization": f"Bearer {self.session_id}"}
        self.client.post("/logout/", headers=headers, json={"username": "alice", "password": "123"})

class WebUserB(HttpUser):
    host = f"http://{REST_HOST}:{REST_PORT}"
    tasks = {PostTasksAnother: 1}  # весами регулируем вероятность

    def on_start(self):
        response = self.client.post("/login/", name="/userlogin",
                         json={"username": "alice", "password": "123"}
                         )
        self.session_id = response.json().get("session_id")
    def on_stop(self):
        headers = {"Authorization": f"Bearer {self.session_id}"}
        self.client.post("/logout/", headers=headers, json={"username": "alice", "password": "123"})

if __name__ == "__main__":
    run_single_user(WebUserA)