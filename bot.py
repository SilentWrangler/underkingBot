import interactions
import dice
from asgiref.sync import sync_to_async
from interactions import (Extension, OptionType, Modal, ShortText,
                          ParagraphText, SlashContext, Embed, StringSelectMenu,
                          StringSelectOption, ActionRow, Button, ButtonStyle, Attachment, slash_option,
                          AutocompleteContext)
from interactions.api.events import Startup, Component

from game.models import Item, Describable, Character


class CharacterExtension(Extension):
    @interactions.listen(Startup)
    async def on_ready(self):
        print(f"Ready! Owned by {self.bot.owner}")

    @interactions.slash_command(
        name='roll',
        description='Roll the dice!'
    )
    @interactions.slash_option(
        name='formula',
        description='Dice roll formula, like 4d6 or d20+3',
        opt_type=OptionType.STRING,
    )
    async def roll(self, ctx: SlashContext, formula: str):
        try:
            result = dice.roll(formula)
            await ctx.send(f'{formula}: {result} ')
        except dice.DiceBaseException as e:
            await ctx.send(e.pretty_print())

    @interactions.slash_command(
        name='create',
        group_description='Создание записи в БД'
    )
    async def create(self, ctx: SlashContext):
        await ctx.send('Выберите сущность для создания!')

    @interactions.slash_command(
        name='edit',
        group_description='Изменение записи в БД'
    )
    async def edit(self, ctx: SlashContext):
        await ctx.send('Выберите сущность для создания!')

    @create.subcommand(
        sub_cmd_name='item'
    )
    @slash_option(
        name='image',
        description='Изображение предмета',
        required=False,
        opt_type=OptionType.ATTACHMENT
    )
    async def create_item(self, ctx: SlashContext, image: Attachment = None):
        await self.modify_or_create_item(ctx, image)

    @edit.subcommand(
        sub_cmd_name='item'
    )
    @slash_option(
        name='name',
        description='Имя предмета',
        required=True,
        opt_type=OptionType.STRING,
        autocomplete=True
    )
    @slash_option(
        name='image',
        description='Новое изображение предмета',
        required=False,
        opt_type=OptionType.ATTACHMENT
    )
    async def edit_item(self, ctx: SlashContext, name: str, image: Attachment = None):
        item = await sync_to_async(Item.objects.get)(name=name)
        await self.modify_or_create_item(ctx, image, item)

    async def modify_or_create_item(self,ctx: SlashContext, image: Attachment = None, item: Item = None):
        if item is None:
            item = Item()
            modal = name_description_modal('Создать вещь', effectable=True)
        else:
            modal = name_description_modal('Изменить вещь', effectable=True
                                           , name=item.name, description=item.description,
                                           level=str(item.level),effect=item.effect)

        await ctx.send_modal(modal)
        modal_ctx = await self.bot.wait_for_modal(modal)
        try:

            if image is not None:
                item.image_url = image.url
            item.name = modal_ctx.responses["name"]
            item.description = modal_ctx.responses["description"]
            item.level = int(modal_ctx.responses['level'])
            item.effect = modal_ctx.responses['effect']
            options = [StringSelectOption(label='-', value='-'),
                       StringSelectOption(label='L', value='L')]
            options.extend([StringSelectOption(label=str(i), value=str(i)) for i in range(1, 21)])
            components = StringSelectMenu(*options)
            msg = await modal_ctx.send(content="", embeds=[to_embed(item)], components=components)

            comp = await self.bot.wait_for_component(msg)
            bulk = comp.ctx.values[0]
            item.txt_to_bulk(bulk)

            await sync_to_async(item.save, thread_sensitive=True)()
            await comp.ctx.edit_origin(content="", embeds=[to_embed(item)], components=[])

        except ValueError as ex:
            print(ex)
            await modal_ctx.send('Уровень должен быть числом!', ephemeral=True)
    @create.subcommand(
        sub_cmd_name='character'
    )
    @slash_option(
        name='image',
        description='Изображение персонажа',
        required=False,
        opt_type=OptionType.ATTACHMENT
    )
    async def create_character(self, ctx: SlashContext, image: Attachment = None):
        await self.modify_or_create_character(ctx, image, set_author=True)

    @edit.subcommand(
        sub_cmd_name='character'
    )
    @slash_option(
        name='name',
        description='Имя персонажа',
        required=True,
        opt_type=OptionType.STRING,
        autocomplete=True
    )
    @slash_option(
        name='image',
        description='Новое изображение персонажа',
        required=False,
        opt_type=OptionType.ATTACHMENT
    )
    async def edit_character(self, ctx: SlashContext, name: str, image: Attachment = None):
        character = await sync_to_async(Character.objects.get)(name=name)
        await self.modify_or_create_character(ctx, image, character)

    async def modify_or_create_character(self, ctx: SlashContext, image:Attachment=None, character = None, set_author = False):
        if character is None:
            character = Character()
            modal = name_description_modal('Создать персонажа')
        else:
            modal = name_description_modal('Изменить персонажа', name=character.name,
                                           description=character.description, level=str(character.level))
        await ctx.send_modal(modal)
        modal_ctx = await self.bot.wait_for_modal(modal)

        try:

            if image is not None:
                character.image_url = image.url
            if set_author:
                character.discord_id = int(ctx.author_id)
            character.name = modal_ctx.responses["name"]
            character.description = modal_ctx.responses["description"]
            character.level = int(modal_ctx.responses['level'])
            stats1 = [('strength', 'Сила'), ('dexterity', 'Ловкость'), ('constitution', 'Телосложение')]
            components = []
            stat_range = [i for i in range(6, 22, 2)] + [21, 22]
            for stat_id, stat in stats1:
                options = [StringSelectOption(label=f'{i}', value=f'{i}') for i in stat_range]
                components.append(ActionRow(StringSelectMenu(*options, placeholder=stat, custom_id=stat_id)))
            components.append(ActionRow(Button(label='Далее', custom_id='next', style=ButtonStyle.GREEN)))
            msg = await modal_ctx.send(content='', embeds=[to_embed(character)], components=components)

            finished = False
            comp = await self.bot.wait_for_component(msg)
            first = True
            while not finished:
                if first:
                    first = False
                else:
                    comp = await self.bot.wait_for_component(msg)

                if comp.ctx.custom_id == 'next':
                    finished = True
                else:
                    character.__setattr__(comp.ctx.custom_id, int(comp.ctx.values[0]))
                    await comp.ctx.edit_origin(content="",
                                               embeds=[to_embed(character)], components=components)

            stats2 = [('intelligence', 'Интеллект'), ('wisdom', 'Мудрость'), ('charisma', 'Харизма')]
            components = []
            for stat_id, stat in stats2:
                options = [StringSelectOption(label=f'{i}', value=f'{i}') for i in stat_range]
                components.append(ActionRow(StringSelectMenu(*options, placeholder=stat, custom_id=stat_id)))
            components.append(ActionRow(Button(label='Далее', custom_id='next', style=ButtonStyle.GREEN)))
            await comp.ctx.edit_origin(content="", embeds=[to_embed(character)], components=components)

            finished = False
            comp = await self.bot.wait_for_component(msg)
            first = True
            while not finished:
                if first:
                    first = False
                else:
                    comp = await self.bot.wait_for_component(msg)

                if comp.ctx.custom_id == 'next':
                    finished = True
                else:
                    character.__setattr__(comp.ctx.custom_id, int(comp.ctx.values[0]))
                    await comp.ctx.edit_origin(content="",
                                               embeds=[to_embed(character)], components=components)

            await comp.ctx.edit_origin(content="", embeds=[to_embed(character)], components=[])
            await sync_to_async(character.save, thread_sensitive=True)()

        except ValueError as ex:
            await modal_ctx.send('Уровень должен быть числом!', ephemeral=True)

    @interactions.slash_command(
        name='view',
        group_description='Просмотр записи в БД'
    )
    async def view(self, ctx: SlashContext):
        await ctx.send('Выберите сущность для просмотра!')

    @view.subcommand(
        sub_cmd_name='character'
    )
    @slash_option(
        name='name',
        description='Имя персонажа',
        required=True,
        opt_type=OptionType.STRING,
        autocomplete=True
    )
    async def view_character(self, ctx: SlashContext, name: str):
        character = await sync_to_async(Character.objects.get)(name=name)
        await ctx.send(embeds=[to_embed(character)])

    @view_character.autocomplete("name")
    @edit_character.autocomplete('name')
    async def vc_autocomplete(self, ctx: AutocompleteContext):
        search = ctx.input_text

        filtered = await sync_to_async(list)(Character.objects.filter(name__icontains=search)[:10])
        choices = [dict(name=c.name, value=c.name) for c in filtered]

        await ctx.send(choices=choices)

    @view.subcommand(
        sub_cmd_name='item'
    )
    @slash_option(
        name='name',
        description='Имя предмета',
        required=True,
        opt_type=OptionType.STRING,
        autocomplete=True
    )
    async def view_item(self, ctx: SlashContext, name: str):
        item = await sync_to_async(Item.objects.get)(name=name)
        await ctx.send(embeds=[to_embed(item)])

    @view_item.autocomplete('name')
    @edit_item.autocomplete('name')
    async def vi_autocomplete(self, ctx: AutocompleteContext):
        search = ctx.input_text

        filtered = await sync_to_async(list)(Item.objects.filter(name__icontains=search)[:10])
        choices = [dict(name=c.name, value=c.name) for c in filtered]

        await ctx.send(choices=choices)

def name_description_modal(title, leleved=True, effectable=False, **defaults):
    components = [ShortText(label='Имя', custom_id='name', max_length=256, value=defaults.get('name', None)),
                  ParagraphText(label='Описание', custom_id='description', max_length=2000, value=defaults.get('description', None))]
    if leleved:
        components.append(ShortText(label='Уровень', custom_id='level', value=defaults.get('level', None)))
    if effectable:
        components.append(ShortText(label='Эффект', custom_id='effect', value=defaults.get('effect', None)))
    modal = Modal(
        *components,
        title=title,
    )
    return modal


def to_embed(entity: Describable):
    base_embed = Embed()
    base_embed.title = entity.name
    base_embed.add_field(entity_type_name(entity), value=' ')
    base_embed.add_field('Описание', entity.description)
    if entity.image_url:
        base_embed.set_image(entity.image_url)
    if isinstance(entity, Character):
        base_embed.add_field('Характеристики',
                             f'\
Сила: {entity.strength} ({((entity.strength - 10) // 2)})\n\
Ловкость: {entity.dexterity} ({(entity.dexterity - 10) // 2})\n\
Телосложение: {entity.constitution} ({(entity.constitution - 10) // 2})\n\
Интеллект: {entity.intelligence} ({(entity.intelligence - 10) // 2})\n\
Мудрость: {entity.wisdom} ({(entity.wisdom - 10) // 2})\n\
Харизма: {entity.charisma} ({(entity.charisma - 10) // 2})'
                             )
    if isinstance(entity, Item):
        base_embed.add_field('Масса', entity.bulk_txt)
    if hasattr(entity, 'effect'):
        base_embed.add_field('Эффект', entity.effect)
    return base_embed


def entity_type_name(entity):
    if isinstance(entity, Character):
        if entity.character_class is not None:
            return f'{entity.character_class.name}'
    if hasattr(entity, 'level'):
        return f'{entity.__class__.__name__} {entity.level}'
    return entity.__class__.__name__
