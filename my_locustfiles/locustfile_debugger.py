from locust import HttpUser, TaskSet, task, events, tag, constant_pacing, run_single_user
import sys, os
from locust_influxdb_listener import InfluxDBListener, InfluxDBSettings
import yaml
import platform

import logging
from http.client import HTTPConnection
HTTPConnection.debuglevel = 1
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

#Определим что мы либо запустили тест к режиме дебага или нет
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
    wait_time = constant_pacing(5)

    @task
    @tag('posts')
    def view_posts(self):
        with self.client.post("/posts/1/", name="/posts",
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
# ===================
# Основные пользователи
# ===================

class BaseWebUser(HttpUser):
    #wait_time = constant_throughput(1)
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

if __name__ == "__main__":
    run_single_user(BaseWebUser)