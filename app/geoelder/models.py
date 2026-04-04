from django.db import models
from django.contrib.auth.models import User 

class Lar(models.Model):
    nome = models.CharField(max_length=100)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # A área segura agora pertence ao LAR
    center_lat = models.FloatField(default=41.3333)
    center_lng = models.FloatField(default=-8.2354)
    radius = models.IntegerField(default=500) # 500 metros por defeito
    def __str__(self):
        return self.nome
    
class Velhinho(models.Model):
    sexo_opcoes = [('F', 'Feminino'), ('M', 'Masculino')]
    
    nome = models.CharField(max_length=100)
    lar = models.ForeignKey(Lar, on_delete=models.CASCADE)
    idade = models.IntegerField()
    sexo = models.CharField(max_length=1, choices=sexo_opcoes)
    doencas = models.CharField(max_length=300)
    daily_step_goal = models.IntegerField(default=2000)
    def __str__(self):
        return self.nome
    

class Localizacao(models.Model):
    velhinho= models.ForeignKey(Velhinho, on_delete=models.CASCADE)
    latitude=models.FloatField()
    longitude=models.FloatField()
    passos=models.IntegerField(default=0)
    timestamp=models.DateTimeField(auto_now=True)
def __str__(self):
        return f"Posição de {self.velhinho.nome} em {self.timestamp}"
