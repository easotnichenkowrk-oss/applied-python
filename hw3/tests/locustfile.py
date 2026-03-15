from locust import HttpUser, task, between
import random
import string

class ShortenerLoadTest(HttpUser):
    wait_time = between(0.5, 2)
    
    def on_start(self):
        self.test_alias = "load" + ''.join(random.choices(string.digits, k=4))
        self.client.post("/links/shorten", json={
            "original_url": "https://yandex.ru",
            "custom_alias": self.test_alias
        }, headers={"x-token": "loaduser"})

    @task(1)
    def create_random_link(self):
        alias = ''.join(random.choices(string.ascii_letters, k=8))
        self.client.post("/links/shorten", json={
            "original_url": "https://github.com",
            "custom_alias": alias
        }, headers={"x-token": "loaduser"})

    @task(5)
    def redirect_link(self):
        self.client.get(f"/links/{self.test_alias}", name="/links/[short_code]", allow_redirects=False)