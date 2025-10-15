from locust import HttpUser, User, TaskSet, task, constant_throughput, events, tag, constant_pacing
import grpc, time, sys, os
from locust_influxdb_listener import InfluxDBListener, InfluxDBSettings
import yaml
import platform

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
    influxDBSettings = InfluxDBSettings(
        host = INFLUX_HOST,#localhost
        port = INFLUX_PORT,
        influx_host=INFLUX_HOST,#localhost
        influx_port=INFLUX_PORT,
        user = 'myusername',
        pwd = 'passwordpasswordpassword',
        database = 'influxDatabase',
        interval_ms=100
    )
    # start listerner with the given configuration
    InfluxDBListener(env=environment, influxDbSettings=influxDBSettings)
    print(f"InfluxDBListener host: {influxDBSettings.host}")

class UserTasks(TaskSet):
    wait_time = constant_throughput(0.1)

    @task(3)
    @tag('users')
    def users_info(self):
        self.client.get("/users/1", name="/users")

    @task(3)
    def stop(self):
        self.interrupt()

class PostTasks(TaskSet):
    wait_time = constant_throughput(0.1)

    @task(1)
    @tag('posts')
    def view_posts(self):
        self.client.post("/posts/1/", name="/posts",
                         json={"title": "Ruslan", "body": "bar", "userId": "1"})
    @task(1)
    def stop(self):
        self.interrupt()
# ===================
# Основные пользователи
# ===================

class BaseWebUser(HttpUser):
    wait_time = constant_throughput(1)
    tasks = {UserTasks: 3, PostTasks: 1}  # весами регулируем вероятность

    def on_start(self):
        response = self.client.post("/login/", name="/userlogin",
                         json={"username": "alice", "password": "123"}
                         )
        self.session_id = response.json().get("session_id")
    def on_stop(self):
        headers = {"Authorization": f"Bearer {self.session_id}"}
        self.client.post("/logout/", headers=headers, json={"username": "alice", "password": "123"})

class AdminUser(HttpUser):
    wait_time = constant_pacing(1)

    @task
    @tag('admin')
    def admin_login(self):
        response = self.client.post("/login/", name="/adminlogin",
                         json={"username": "ruslan", "password": "123"})
        self.session_id = response.json().get("session_id")
# ===================
# gRPC User
# ===================

class GRPCUser(User):
    wait_time = constant_throughput(1)

    def on_start(self):
        self.channel = grpc.insecure_channel(f"{GRPC_HOST}:{GRPC_PORT}")
        self.stub = helloworld_pb2_grpc.GreeterStub(self.channel)

    def on_stop(self):
        self.channel.close()

    @task
    def say_hello(self):
        start_time = time.time()
        response = None
        exception = None  # <-- Инициализируем переменную заранее
        try:
            request = helloworld_pb2.HelloRequest(name="LocustUser")
            response = self.stub.SayHello(request)
        except Exception as e:
            exception = e
        finally:
            total_time = (time.time() - start_time) * 1000
            response_length = len(response.message) if response else 0

            events.request.fire(
                request_type="GRPC",
                name="SayHello",
                response_time=total_time,
                response_length=response_length,
                response=response,
                context={},
                exception=exception,
                start_time=start_time,
                url=f"{GRPC_HOST}:{GRPC_PORT}"
            )