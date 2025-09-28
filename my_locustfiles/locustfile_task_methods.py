#Образец как можно обходиться без декораторов @tasks, заданных в locustfile_1 создавая функции и 
#далее описывая их в атрибуте [tasks] - который Locust воспринимает как 
import time
from locust import HttpUser, constant_pacing, constant

#url https://jsonplaceholder.typicode.com
def users_info(user):
        user.client.get("/users/3")
        user.client.get("/users/4")

def put_posts(user):
    '''аттрибут name нужен для того, чтобы для сгруппировать в 1 транзакцию'''
    for item_id in range(6):
        user.client.put(f"/posts/{item_id+1}",
                        name="/posts",
                        json={"title": "foo", "body": "bar", "userId": item_id+1}
                        )
        time.sleep(1)

class MyUser(HttpUser):
    #wait_time = constant(1)#задает время ожидания для каждого пользователя между транзакциями после каждой транзакции
    wait_time = constant_pacing(1)#задает время ожидания для каждого пользователя между транзакциями включая время выполнения транзакции

    tasks = {
         users_info: 6,#этот метод для пользователя будет вызван в 6 раз чаще
         put_posts: 1
    }
    def on_start(self):
        '''метод вызывается для каждого пользователя перед тем как выйти на нагрузку'''
        self.client.get("/comments?postId=1")

    def on_stop(self):
        '''метод вызывается для каждого пользователя'''
        self.client.get("/comments?postId=2")