import interactions
import dice
from asgiref.sync import sync_to_async
from interactions import Extension, OptionType, Modal, ShortText, ParagraphText, SlashContext, Embed, StringSelectMenu
from interactions.api.events import Startup

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
            result = int(dice.roll(formula))
            await ctx.send(f'{formula}: {result}')
        except dice.DiceBaseException as e:
            await ctx.send(e.pretty_print())

    @interactions.slash_command(
        name='create',
        group_description='Создание записи в БД'
    )
    async def create(self, ctx: SlashContext):
        await ctx.send('Выберите сущность для создания!')

    @create.subcommand(
        sub_cmd_name='item'
    )
    async def create_item(self, ctx: SlashContext):
        modal = name_description_modal('Создать вещь')
        await ctx.send_modal(modal)
        modal_ctx = await self.bot.wait_for_modal(modal)
        try:
            item = Item()
            item.name = modal_ctx.responses["name"]
            item.description = modal_ctx.responses["description"]
            item.level = int(modal_ctx.responses['level'])

            options = ['-', 'L']
            options.extend([str(i) for i in range(1, 21)])
            components = StringSelectMenu(*options)
            await modal_ctx.send(embeds=[to_embed(item)], components=components)
            comp = await self.bot.wait_for_component()
            item.bulk = item.txt_to_bulk(comp.ctx.values[0])
            await sync_to_async(item.save, thread_sensitive=True)()
        except ValueError as ex:
            await modal_ctx.send('Уровень должен быть числом!', ephemeral=True)

    @create.subcommand(
        sub_cmd_name='character'
    )
    async def create_character(self, ctx: SlashContext):
        modal = name_description_modal('Создать персонажа')
        await ctx.send_modal(modal)
        modal_ctx = await self.bot.wait_for_modal(modal)
        try:
            character = Character()
            character.name = modal_ctx.responses["name"]
            character.description = modal_ctx.responses["description"]
            character.level = int(modal_ctx.responses['level'])

        except ValueError as ex:
            await modal_ctx.send('Уровень должен быть числом!', ephemeral=True)
def name_description_modal(title, leleved=True):
    components = [ShortText(label='Имя', custom_id='name', max_length=256),
                  ParagraphText(label='Описание', custom_id='description', max_length=2000)]
    if leleved:
        components.append(ShortText(label='Уровень', custom_id='level'))
    modal = Modal(
        *components,
        title=title,
    )
    return modal


def to_embed(entity: Describable):
    base_embed = Embed()
    base_embed.title = entity.name
    base_embed.add_field(entity_type_name(entity), value='')
    base_embed.add_field('Описание', entity.description)
    if entity.image:
        base_embed.set_image(entity.image)
    if isinstance(entity, Character):
        base_embed.add_field('Характеристики',
                             f'\
Сила: {entity.strength} ({(entity.strength - 10) / 2})\n\
Ловкость: {entity.dexterity} ({(entity.dexterity - 10) / 2})\n\
Телосложение: {entity.constitution} ({(entity.constitution - 10) / 2})\n\
Интеллект: {entity.intelligence} ({(entity.intelligence - 10) / 2})\n\
Мудрость: {entity.wisdom} ({(entity.wisdom - 10) / 2})\n\
Харизма: {entity.charisma} ({(entity.charisma - 10) / 2})'
                             )
    if isinstance(entity, Item):
        base_embed.add_field('Масса', entity.bulk_txt)
    if hasattr(entity,'effect'):
        base_embed.add_field('Эффект', entity.effect)
    return base_embed


def entity_type_name(entity):
    if isinstance(entity, Character):
        if entity.character_class is not None:
            return f'{entity.character_class.name}'
    if hasattr(entity, 'level'):
        return f'{entity.__class__.__name__} {entity.level}'
    return entity.__class__.__name__
