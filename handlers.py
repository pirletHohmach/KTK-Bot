import json
import random
import database


from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from inline_keyboards import GroupChoice
from inline_keyboards import create_group_keyboard
from inline_keyboards import create_help_keyboard


with open('config.json', 'r', encoding="utf-8") as config_file:
    config = json.load(config_file)


username_jokes = config["USERNAME_JOKES"]
SCHEDULE_API_URL = config["SCHEDULE_API_URL"]
COLLEGE_GROUPS = sorted(config["COLLEGE_GROUPS"])
ADMINS = config["ADMIN"]
BUTTONS_PER_PAGE = 8
router = Router()


@router.message(Command('start'))
async def start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    if database.check_user(user_id):
        await message.answer(f"{random.choice(username_jokes)} уже присутствует в базе данных")
    else:
        database.add_user(user_id, username, first_name, last_name, None)

        await message.answer(f"{random.choice(username_jokes)} добавлен в базу данных")
        await message.answer(f"{random.choice(username_jokes)} выбери свою группу с такими же как и ты или напиши:\n", reply_markup=await create_group_keyboard())
        await state.set_state(GroupChoice.waiting_group)


@router.message(Command('help'))
async def help_command(message: Message):
    await message.answer(f"Список доступных команд:", reply_markup=await create_help_keyboard())


@router.message(F.text.startswith("Рассылка") | F.caption.startswith("Рассылка"))
async def broadcast_message(message: Message):
    # Проверка на админа
    if message.from_user.id not in ADMINS:
        await message.answer("У вас нет прав для выполнения этой команды")
        return

    # Список ID пользователей, которым не нужно отправлять рассылку
    excluded_users = [1514066424, 5511030665]

    # Получаем контент после слова "Рассылка" либо из текста, либо из подписи к медиа
    content = ""
    if message.text:
        content = message.text[9:].strip()
    elif message.caption:
        content = message.caption[9:].strip()

    print(f"Debug: Message type detection:")
    print(f"Has photo: {bool(message.photo)}")
    print(f"Has video: {bool(message.video)}")
    print(f"Has document: {bool(message.document)}")
    print(f"Content: {content}")

    # Получаем все ID пользователей из базы
    user_ids = database.get_all_user_ids()
    # Фильтруем список, исключая указанных пользователей
    user_ids = [user_id for user_id in user_ids if user_id not in excluded_users]

    successful = 0
    failed = 0

    try:
        if message.photo:
            photo = message.photo[-1]
            print(f"Debug: Sending photo with file_id: {photo.file_id}")
            for user_id in user_ids:
                try:
                    await message.bot.send_photo(
                        chat_id=user_id,
                        photo=photo.file_id,
                        caption=content if content else None
                    )
                    successful += 1
                except Exception as e:
                    print(f"Ошибка отправки фото пользователю {user_id}: {str(e)}")
                    failed += 1

        elif message.video:
            print(f"Debug: Sending video with file_id: {message.video.file_id}")
            for user_id in user_ids:
                try:
                    await message.bot.send_video(
                        chat_id=user_id,
                        video=message.video.file_id,
                        caption=content if content else None
                    )
                    successful += 1
                except Exception as e:
                    print(f"Ошибка отправки видео пользователю {user_id}: {str(e)}")
                    failed += 1

        elif message.document:
            print(f"Debug: Sending document with file_id: {message.document.file_id}")
            for user_id in user_ids:
                try:
                    await message.bot.send_document(
                        chat_id=user_id,
                        document=message.document.file_id,
                        caption=content if content else None
                    )
                    successful += 1
                except Exception as e:
                    print(f"Ошибка отправки документа пользователю {user_id}: {str(e)}")
                    failed += 1

        else:  # Только текст
            for user_id in user_ids:
                try:
                    await message.bot.send_message(
                        chat_id=user_id,
                        text=content
                    )
                    successful += 1
                except Exception as e:
                    print(f"Ошибка отправки сообщения пользователю {user_id}: {str(e)}")
                    failed += 1

    except Exception as e:
        error_msg = f"Произошла ошибка при рассылке: {str(e)}"
        print(error_msg)
        await message.answer(error_msg)
        return

    # Отправляем статистику админу
    total = successful + failed
    stats = (
        f"Рассылка завершена!\n"
        f"Успешно отправлено: {successful}\n"
        f"Ошибок отправки: {failed}\n"
        f"Всего получателей: {total}"
    )
    print(stats)
    await message.answer(stats)

@router.message(F.text.lower() == "прикол")
async def prikol(message: Message):
    art_no_4 = '''              .,-:;//;:=,
          . :H@@@MM@M#H/.,+%;,
       ,/X+ +M@@M@MM%=,-%HMMM@X/,
     -+@MM; $M@@MH+-,;XMMMM@MMMM@+-
    ;@M@@M- XM@X;. -+XXXXXHHH@M@M#@/.
  ,%MM@@MH ,@%=             .---=-=:=,.
  =@#@@@MX.,                -%HX$$%%%:;
 =-./@M@M$                   .;@MMMM@MM:
 X@/ -$MM/                    . +MM@@@M$
,@M@H: :@:                    . =X#@@@@-
,@@@MMX, .                    /H- ;@M@M=
.H@@@@M@+,                    %MM+..%#$.
 /MMMM@MMH/.                  XM@MH; =;
  /%+%$XHH@$=              , .H@@@@MX,
   .=--------.           -%H.,@@@@@MX,
   .%MM@@@HHHXX$$$%+- .:$MMX =M@@MM%.
     =XMMM@MM@MM#H;,-+HMM@M+ /MMMX=
       =%@M@M#@$-.=$@MM@@@M; %M%=
         ,:+$+-,/H#MMMMMMM@= =,
               =++%%%%+/:-.'''

    art_no_2 = '''
             =+$HM####@H%;,
          /H###############M$,
          ,@################+
           .H##############+
             X############/
              $##########/
               %########/
                /X/;;+X/

                 -XHHX-
                ,######,
#############X  .M####M.  X#############
##############-   -//-   -##############
X##############%,      ,+##############X
-##############X        X##############-
 %############%          %############%
  %##########;            ;##########%
   ;#######M=              =M#######;
    .+M###@,                ,@###M+.
       :XH.                  .HX:
       '''

    art_no_3 = '''
                 =/;;/-
                +:    //
               /;      /;
              -X        H.
.//;;;:;;-,   X=        :+   .-;:=;:;%;.
M-       ,=;;;#:,      ,:#;;:=,       ,@
:%           :%.=/++++/=.$=           %=
 ,%;         %/:+/;,,/++:+/         ;+.
   ,+/.    ,;@+,        ,%H;,    ,/+,
      ;+;;/= @.  .H##X   -X :///+;
      ;+=;;;.@,  .XM@$.  =X.//;=%/.
   ,;:      :@%=        =$H:     .+%-
 ,%=         %;-///==///-//         =%,
;+           :%-;;;;;;;;-X-           +:
@-      .-;;;;M-        =M/;;;-.      -X
 :;;::;;-.    %-        :+    ,-;;-;:==
              ,X        H.
               ;/      %=
                //    +;
                 ,////,
                 '''

    y_linkersdid_poyavilsa_paren = '''
                          .,---.
                        ,/XM#MMMX;,
                      -%##########M%,
                     -@######%  $###@=
      .,--,         -H#######$   $###M:
   ,;$M###MMX;     .;##########$;HM###X=
,/@###########H=      ;################+
-+#############M/,      %##############+
%M###############=      /##############:
H################      .M#############;.
@###############M      ,@###########M:.
X################,      -$=X#######@:
/@##################%-     +######$-
.;##################X     .X#####+,
 .;H################/     -X####+.
   ,;X##############,       .MM/
      ,:+$H@M#######M#$-    .$$=
           .,-=;+$@###X:    ;/=.
                  .,/X$;   .::,
                      .,    ..
    '''


    art_no_5 = '''
                      -$-
                    .H##H,
                   +######+
                .+#########H.
              -$############@.
            =H###############@  -X:
          .$##################:  @#@-
     ,;  .M###################;  H###;
   ;@#:  @###################@  ,#####:
 -M###.  M#################@.  ;######H
 M####-  +###############$   =@#######X
 H####$   -M###########+   :#########M,
  /####X-   =########%   :M########@/.
    ,;%H@X;   .$###X   :##MM@%+;:-
                 ..
  -/;:-,.              ,,-==+M########H
 -##################@HX%%+%%$%%%+:,,
    .-/H%%%+%%$H@###############M@+=:/+:
/XHX%:#####MH%=    ,---:;;;;/&&XHM,:###$
$@#MX %+;- 
    '''

    art_no_6 = '''
                                    :X-
                                  :X###
                                ;@####@
                              ;M######X
                            -@########$
                          .$##########@
                         =M############-
                        +##############$
                      .H############$=.
         ,/:         ,M##########M;.
      -+@###;       =##########M;
   =%M#######;     :#########M/
-$M###########;   :########/
 ,;X###########; =#######$.
     ;H#########+######M=
       ,+#############+
          /M########@-
            ;M#####%
              +####:
               ,$M-
    '''

    art_no_7 = '''
            .+
             /M;
              H#@:              ;,
              -###H-          -@/
               %####$.  -;  .%#X
                M#####+;#H :M#M.
..          .+/;%#############-
 -/%H%+;-,    +##############/
    .:$M###MH$%+############X  ,--=;-
        -/H#####################H+=.
           .+#################X.
         =%M####################H;.
            /@###############+;;/%%;,
         -%###################$
       ;H######################M=
    ,%#####MH$%;+#####M###-/@####%
  :$H%+;=-      -####X.,H#   -+M##@-
 .              ,###;    ;      =$##+
                .#H,               :XH,
                 +                   .;-
    '''

    art_no_8 = '''
           .-;+$XHHHHHHX$+;-.
        ,;X@@X%/;=----=:/%X@@X/,
      =$@@%=.              .=+H@X:
    -XMX:                      =XMX=
   /@@:                          =H@+
  %@X,                            .$@$
 +@X.                               $@%
-@@,                                .@@=
%@%                                  +@$
H@:                                  :@H
H@:         :HHHHHHHHHHHHHHHHHHX,    =@H
%@%         ;@M@@@@@@@@@@@@@@@@@H-   +@$
=@@,        :@@@@@@@@@@@@@@@@@@@@@= .@@:
 +@X        :@@@@@@@@@@@@@@@M@@@@@@:%@%
  $@$,      ;@@@@@@@@@@@@@@@@@M@@@@@@$.
   +@@HHHHHHH@@@@@@@@@@@@@@@@@@@@@@@+
    =X@@@@@@@@@@@@@@@@@@@@@@@@@@@@X=
      :$@@@@@@@@@@@@@@@@@@@M@@@@$:
        ,;$@@@@@@@@@@@@@@@@@@X/-
           .-;+$XXHHHHHX$+;-.
    '''

    art_no_9 = '''
             ,:/+/-
            /M/              .,-=;//;-
       .:/= ;MH/,    ,=/+%$XH@MM#@:
      -$##@+$###@H@MMM#######H:.    -/H#
 .,H@H@ X######@ -H#####@+-     -+H###@X
  .,@##H;      +XM##M/,     =%@###@X;-
X%-  :M##########$.    .:%M###@%:
M##H,   +H@@@$/-.  ,;$M###@%,          -
M####M=,,---,.-%%H####M$:          ,+@##
@##################@/.         :%H##@$-
M###############H,         ;HM##M$=
#################.    .=$M##M$=
################H..;XM##M$=          .:+
M###################@%=           =+@MH%
@#################M/.         =+H#X%=
=+M###############M,      ,/X#H+:,
  .;XM###########H=   ,/X#H+:;
     .=+HM#######M+/+HM@+=.
         ,:/%XM####H/.
              ,.:=-.
    '''

    arts = [
        f'<pre>{y_linkersdid_poyavilsa_paren}</pre>',
        f'<pre>{art_no_2}</pre>',
        f'<pre>{art_no_3}</pre>',
        f'<pre>{art_no_4}</pre>',
        f'<pre>{art_no_5}</pre>',
        f'<pre>{art_no_6}</pre>',
        f'<pre>{art_no_7}</pre>',
        f'<pre>{art_no_8}</pre>',
        f'<pre>{art_no_9}</pre>'
    ]
    await message.answer(random.choice(arts), parse_mode='HTML')