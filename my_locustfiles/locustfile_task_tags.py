#locustfile_task_tags
import time
from locust import HttpUser, task, constant_pacing, tag

#url https://jsonplaceholder.typicode.com
class QuickstartUser(HttpUser):
    #wait_time = between(1, 5)#задает время ожидания для каждого пользователя между транзакциями
    wait_time = constant_pacing(1)#задает время ожидания для каждого пользователя между транзакциями включая время выполнения транзакции

    #с помощью тэгов можно выбирать какие транзакции будут выполняться а какие нет, пример
    #locust --headless --users 5 --spawn-rate 1 --tags get_users -H https://jsonplaceholder.typicode.com
    #locust --headless --users 5 --spawn-rate 1 --exclude-tags tag1 -H https://jsonplaceholder.typicode.com
    @tag('get_users')
    @task(6)#приоритетность операции выполняется в 6 раз чаще чем те, для которых значение не задано
    def users_info(self):
        self.client.get("/users/2")
        self.client.get("/users/1")

    @tag('tag1','posts')
    @task
    def put_posts(self):
        '''аттрибут name нужен для того, чтобы для сгруппировать в 1 транзакцию'''
        for item_id in range(6):
            self.client.put(f"/posts/{item_id+1}", name="/posts",json={"title": "foo", "body": "bar", "userId": item_id+1})
            time.sleep(1)

    @tag('tag1')
    @task
    def task1(self):
        pass
    
    def on_start(self):
        '''метод вызывается для каждого пользователя перед тем как выйти на нагрузку'''
        self.client.get("/comments?postId=1")

    def on_stop(self):
        '''метод вызывается для каждого пользователя'''
        self.client.get("/comments?postId=2")