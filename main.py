import asyncio
import uuid
from pywebio import start_server
from pywebio.input import *
from pywebio.output import *
from pywebio.session import run_async, run_js
from encrypt import *
from decrypt import *
from encrypt_CBC import *
from decrypt_CBC import *

chats = {}
MAX_USERS_PER_CHAT = 2
MAX_MESSAGES_COUNT = 100


async def main():
    global chats

    put_markdown("## ✉️ Добро пожаловать в мессенджер")

    action = await actions("Выберите действие", buttons=["Создать чат", "Подключиться к чату"])

    if action == "Создать чат":
        mode = await actions("Выберите режим шифрования", buttons=["ECB", "CBC"])
        put_markdown(f"### Выбран режим шифрования: {mode}")
        chat_name = await input("Название чата", required=True, placeholder="Введите название чата")
        chat_id = str(uuid.uuid4())
        chats[chat_id] = {'name': chat_name, 'messages': [], 'users': set(), 'lock': asyncio.Lock(), 'is_deleted': False, 'mode': mode}
        put_markdown(f"### ✅ Чат создан")
        await join_chat(chat_id)
    elif action == "Подключиться к чату":
        chat_id = await input("ID чата", required=True, placeholder="Введите ID существующего чата")
        if chat_id not in chats:
            put_error("Чат с таким ID не найден.")
        else:
            await join_chat(chat_id)


async def join_chat(chat_id):
    global chats
    chat = chats[chat_id]

    async with chat['lock']:
        if len(chat['users']) >= MAX_USERS_PER_CHAT:
            put_error("Чат с таким ID не найден.")
            return

        nickname = await input("Ваше имя", required=True, placeholder="Введите имя")
        chat['users'].add(nickname)

    put_markdown(f"## 💬 Чат: {chat['name']}. <span style='font-size: 20px;'> 🔑 Защищено алгоритмом шифрования RC6 ({chat['mode']}).</span>")

    msg_box = output()
    put_scrollable(msg_box, height=300, keep_bottom=True)

    put_buttons(['Показать ID чата'], onclick=lambda btn: toast(f"ID чата: {chat_id}"))

    put_buttons(['Удалить чат'], onclick=lambda btn: delete_chat(chat_id))

    msg_box.append(put_markdown(f'👤{nickname} присоединился(-лась) к чату'))

    refresh_task = run_async(refresh_msg(chat, nickname, msg_box))

    while True:
        if chat['is_deleted']:
            toast("Чат был удален.")
            run_js('window.location.reload()')
            break

        data = await input_group("💭 Новое сообщение", [
            input(placeholder="Текст сообщения ...", name="msg"),
            actions(name="cmd", buttons=["Отправить"]) 
        ], validate=lambda m: ('msg', "Введите текст сообщения") if m["cmd"] == "Отправить" and not m['msg'] else None)

        if chat['is_deleted']:
            msg_box.append(put_markdown(f'🚫 Чат был удален.'))
            await asyncio.sleep(1)
            break

        msg_box.append(put_markdown(f"{nickname}: {data['msg']}"))
        global encrypt_result
        if chat['mode'] == "ECB":
            encrypt_result = encrypt(data['msg'])
        elif chat['mode'] == "CBC":
            encrypt_result = encrypt_CBC(data['msg'])
        print('(Зашифрованное сообщение, ключ Диффи-Хеллмана):', encrypt_result)
        chat['messages'].append((nickname, encrypt_result))

    refresh_task.close()

    async with chat['lock']:
        chat['users'].remove(nickname)

    if not chat['users']:
        del chats[chat_id]

    put_buttons(['Вернуться в меню'], onclick=lambda btn: run_js('window.location.reload()'))


async def refresh_msg(chat, nickname, msg_box):
    last_idx = len(chat['messages'])

    while True:
        await asyncio.sleep(1)

        for m in chat['messages'][last_idx:]:
            if m[0] != nickname:
                if chat['mode'] == "ECB":
                    decrypted_message = decrypt(m[1], encrypt_result[1])
                elif chat['mode'] == "CBC":
                    decrypted_message = decrypt_CBC(m[1], encrypt_result[1], encrypt_result[2])
                print('Расшифрованное сообщение:', decrypted_message)
                msg_box.append(put_markdown(f"`{m[0]}`: {decrypted_message}"))

        if len(chat['messages']) > MAX_MESSAGES_COUNT:
            chat['messages'] = chat['messages'][len(chat['messages']) // 2:]

        last_idx = len(chat['messages'])


def delete_chat(chat_id):
    global chats
    if chat_id in chats:
        chats[chat_id]['is_deleted'] = True
        del chats[chat_id]
        toast("Чат удален.")
        run_js('window.location.reload()')


if __name__ == "__main__":
    start_server(main, debug=True, port=8080, cdn=False)
