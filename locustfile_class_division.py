#locustfile_test_start_end
import time
from locust import User, HttpUser, task, constant_throughput, events, tag, constant
from locust.runners import MasterRunner
import grpc

import sys
import os

import time

# add gRPC generated files folder to Python path
grpc_folder = r"D:\\GitHub\\gRPC"
sys.path.append(grpc_folder)

import helloworld_pb2
import helloworld_pb2_grpc

#url https://jsonplaceholder.typicode.com

@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """
    Вызывается при запуске самого Locust перед тестами
    Загрузить большой справочник в память (чтобы все пользователи его использовали).
    Установить соединение с внешним сервисом.
    Создать лог-файл именно на воркере.
    На мастере — настроить метрики или логирование.
    """
    if isinstance(environment.runner, MasterRunner):
        print("I'm on master node")
    else:
        print("I'm on a worker or standalone node")

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Вызывается когда тест запускается с веббраузера вызов происходит после нажатия на кнопку [Start]"""
    print("A new test is starting")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Вызывается после завершения теста или при нажатии на кнопку [Stop]"""
    print("A new test is ending")

@events.request.add_listener
def my_request_handler(request_type, name, response_time, response_length, response,
                       context, exception, start_time, url, **kwargs):
    if exception:
        print(f"Request to {name} failed with exception {exception}")
    #else:
    #    print(f"Successfully made a request to: {name}")
    #    print(f"The response was {response.text}")
    if response_time > 1000:
        print("Время при обращении к эндпоинту " + name + " превысило 1 s")

class BaseUser(HttpUser):
    wait_time = constant_throughput(0.1)#задает время ожидания для каждого пользователя между транзакциями
    abstract = True
    def on_start(self):
        '''метод вызывается для каждого пользователя перед тем как выйти на нагрузку'''
        self.client.post("/login/", name= "/userlogin", json={"username":"alice","password":"123"})

    def on_stop(self):
        '''метод вызывается для каждого пользователя'''
        self.client.post("/logout/", json={"username":"alice","password":"123"})

class AdminUser(HttpUser):
    wait_time = constant_throughput(1)
    fixed_count = 1
    @tag('users')
    @task
    def admin_login(self):
        self.client.post("/login/", name= "/adminlogin", json={"username":"ruslan","password":"123"})

class GRPCUser(User):
    wait_time = constant_throughput(1)
    fixed_count = 1
    def on_start(self):
        # подключаемся к серверу один раз на пользователя
        self.channel = grpc.insecure_channel('localhost:50051')
        self.stub = helloworld_pb2_grpc.GreeterStub(self.channel)

    def on_stop(self):
        # закрываем соединение
        self.channel.close()

    @task
    def say_hello(self):
        start_time = time.time()
        try:
            request = helloworld_pb2.HelloRequest(name="LocustUser")
            response = self.stub.SayHello(request)
            total_time = (time.time() - start_time) * 1000  # в миллисекундах

            # регистрируем успешный запрос в статистике Locust
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
            # регистрируем ошибку
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

class UserActionsSerfs(BaseUser):
    weight = 3
    @tag('users')
    @task
    def users_info(self):
        #self.client.get("/users/2")
        self.client.get("/users/1")

class UserActionsPosts(BaseUser):
    weight = 1
    @tag('posts')
    @task
    def view_posts(self):
        '''аттрибут name нужен для того, чтобы для сгруппировать в 1 транзакцию'''
        self.client.post(f"/posts/1/", name="/posts",json={"title": "Ruslan", "body": "bar", "userId": "1"})

