from django.db import models


from django.db import models


class Monster(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    attack_1 = models.CharField(max_length=100)
    attack_2 = models.CharField(max_length=100)
    attack_3 = models.CharField(max_length=100)
    attack_1_description = models.TextField()
    attack_2_description = models.TextField()
    attack_3_description = models.TextField()
    strength = models.CharField(max_length=100)
    weakness = models.CharField(max_length=100)
    image_url = models.URLField(max_length=200)

    def __str__(self):
        return self.name
