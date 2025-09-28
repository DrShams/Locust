from locust import HttpUser, User, TaskSet, task, constant_throughput, events, tag
import grpc, time, sys, os
from locust_influxdb_listener import InfluxDBListener, InfluxDBSettings

grpc_folder = r"D:\\GitHub\\gRPC"
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
        host = 'localhost',
        port = 8086,
        user = 'myusername',
        pwd = 'passwordpasswordpassword',
        database = 'influxDatabase',
        interval_ms=1000
        
        # optional global tags to be added to each metric sent to influxdb
        #additional_tags = {
        #    'environment': 'test',
        #    'some_other_tag': 'tag_value',
        #}
    )
    # start listerner with the given configuration
    InfluxDBListener(env=environment, influxDbSettings=influxDBSettings)
    
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
        #headers = {"Authorization": f"Bearer {self.session_id}"}


class AdminUser(HttpUser):
    wait_time = constant_throughput(0.01)

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
        self.channel = grpc.insecure_channel("localhost:50051")
        self.stub = helloworld_pb2_grpc.GreeterStub(self.channel)

    def on_stop(self):
        self.channel.close()

    @task
    def say_hello(self):
        start_time = time.time()
        try:
            request = helloworld_pb2.HelloRequest(name="LocustUser")
            response = self.stub.SayHello(request)
            total_time = (time.time() - start_time) * 1000

            events.request.fire(
                request_type="GRPC",
                name="SayHello",
                response_time=total_time,
                response_length=len(response.message),
                response=response,
                context={},
                exception=None,
                start_time=start_time,
                url="localhost:50051"
            )
        except Exception as e:
            total_time = (time.time() - start_time) * 1000
            events.request.fire(
                request_type="GRPC",
                name="SayHello",
                response_time=total_time,
                response_length=0,
                response=None,
                context={},
                exception=e,
                start_time=start_time,
                url="localhost:50051"
            )
