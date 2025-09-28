#locustfile_test_start_end
import time
from locust import HttpUser, task, constant_throughput, events, tag, constant
from locust.runners import MasterRunner

#url https://jsonplaceholder.typicode.com

from locust.runners import STATE_STOPPING, STATE_STOPPED, STATE_CLEANUP, MasterRunner, LocalRunner
import gevent

def checker(environment):
    while not environment.runner.state in [STATE_STOPPING, STATE_STOPPED, STATE_CLEANUP]:
        time.sleep(1)
        if environment.runner.stats.total.fail_ratio > 0.8:
            print(f"fail ratio was {environment.runner.stats.total.fail_ratio}, quitting")
            environment.runner.quit()
            return
@events.init.add_listener
def on_locust_init(environment, **_kwargs):
    # dont run this on workers, we only care about the aggregated numbers
    if isinstance(environment.runner, MasterRunner) or isinstance(environment.runner, LocalRunner):
        gevent.spawn(checker, environment)

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Вызывается когда тест запускается с веббраузера вызов происходит после нажатия на кнопку [Start]"""
    print("A new test is starting")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Вызывается после завершения теста или при нажатии на кнопку [Stop]"""
    print("A new test is ending")

#@events.request.add_listener
#def my_request_handler(request_type, name, response_time, response_length, response,
#                       context, exception, start_time, url, **kwargs):
    #if exception:
    #    print(f"Request to {name} failed with exception {exception}")
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

class UserActionsSerfs(BaseUser):
    weight = 3
    @tag('users')
    @task
    def users_info(self):
        #self.client.get("/users/2")
        self.client.get("/users/ava")

class UserActionsPosts(BaseUser):
    weight = 1
    @tag('posts')
    @task
    def view_posts(self):
        '''аттрибут name нужен для того, чтобы для сгруппировать в 1 транзакцию'''
        self.client.post(f"/posts/1/", name="/posts",json={"title": "Ruslan", "body": "bar", "userId": "1"})

