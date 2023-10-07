from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator, MinLengthValidator
from django.utils.translation import gettext as _


# Create your models here.

class Describable(models.Model):
    name = models.CharField(max_length=256, validators=[MinLengthValidator(2)], unique=True)
    description = models.CharField(max_length=2000)
    image_url = models.CharField(max_length=2000, blank=True, null=True)

    class Meta:
        abstract = True


class Effecting(models.Model):
    effect = models.CharField(max_length=300, null=True, blank=True)

    class Meta:
        abstract = True


class Taggable(models.Model):
    tags = models.ManyToManyField('Tag')

    class Meta:
        abstract = True


class Tag(Describable):
    pass


class Character(Describable, Taggable):
    # For bot control
    discord_id = models.BigIntegerField(default=0, null=True, blank=True)
    # Ability Scores
    strength = models.PositiveIntegerField(default=10)
    dexterity = models.PositiveIntegerField(default=10)
    constitution = models.PositiveIntegerField(default=10)
    intelligence = models.PositiveIntegerField(default=10)
    wisdom = models.PositiveIntegerField(default=10)
    charisma = models.PositiveIntegerField(default=10)
    # Ancestry, Heritage, Background
    ancestry = models.ForeignKey('Ancestry', null=True, on_delete=models.SET_NULL)
    background = models.ForeignKey('Background', null=True, on_delete=models.SET_NULL)
    heritage = models.ForeignKey('Heritage', null=True, on_delete=models.SET_NULL)
    # Class
    character_class = models.ForeignKey('Class', null=True, on_delete=models.SET_NULL)
    level = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(20)])
    # Items
    inventory = models.ManyToManyField('Item', through='InventoryEntry', related_name='owners')
    equipment = models.ManyToManyField('Item', through='EquipmentEntry', related_name='wearers')
    # Feats
    feats = models.ManyToManyField('Feat')
    # Spells
    spells = models.ManyToManyField('Spell')
    # Resources
    hp = models.PositiveIntegerField(default=0)
    max_hp = models.PositiveIntegerField(default=0)

    focus_points = models.PositiveIntegerField(default=0)
    max_focus = models.PositiveIntegerField(default=0)

    hero_points = models.PositiveIntegerField(default=0)


class Item(Describable, Effecting, Taggable):
    bulk = models.IntegerField(default=-1, validators=[MinValueValidator(-1)])
    level = models.PositiveIntegerField(default=0)

    @property
    def bulk_txt(self):
        if self.bulk == -1:
            return _("-")
        elif self.bulk == 0:
            return _("L")
        else:
            return str(self.bulk)

    def txt_to_bulk(self, value: str):
        if value.startswith('-'):
            self.bulk = -1
        elif value.upper().startswith('L'):
            self.bulk = 0
        else:
            pre_bulk = int(value)
            if pre_bulk < 0:
                self.bulk = -1
            else:
                self.bulk = pre_bulk


class InventoryEntry(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    character = models.ForeignKey(Character, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def total_bulk_txt(self):
        if self.item.bulk == -1:
            return '-'
        elif self.item.bulk == 0:
            return f'{self.quantity//10} {self.quantity%10}L'
        else:
            return f'{self.quantity * self.item.bulk}'


class EquipmentEntry(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    character = models.ForeignKey(Character, on_delete=models.CASCADE)
    slot = models.CharField(max_length=100)


class Feat(Describable, Effecting, Taggable):
    level = models.PositiveIntegerField(default=1)


class Class(Describable):
    features = models.ManyToManyField('Feat')
    tag = models.OneToOneField(Tag, null=True, on_delete=models.SET_NULL, related_name='linked_class')


class Action(Describable, Taggable, Effecting):
    length = models.CharField(max_length=50)
    related_feat = models.ForeignKey(Feat, null=True, blank=True, on_delete=models.CASCADE)


class Spell(Describable, Taggable, Effecting):
    level = models.PositiveIntegerField(default=0)


class SpellSlot(models.Model):
    character = models.ForeignKey(Character, related_name='prepared_spells', on_delete=models.CASCADE)
    level = models.PositiveIntegerField(default=0)
    spell = models.ForeignKey('Spell', null=True, on_delete=models.SET_NULL)
    spontaneous = models.BooleanField(default=False)
    is_cast = models.BooleanField(default=False)


class Ancestry(Describable, Effecting, Taggable):
    tag = models.OneToOneField(Tag, null=True, on_delete=models.SET_NULL, related_name='linked_ancestry')


class Background(Describable, Taggable, Effecting):
    pass


class Heritage(Describable, Taggable, Effecting):
    pass
