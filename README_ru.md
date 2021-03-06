``TODO: доролнить ссылками на код``

### API для фоновых операций в openstack, основанное на Futures.
-----------------------------------------------------------------

#### Abstract
-------------

There a set of openstack api functions which starts background actions
and return preliminary results - like 'novaclient.create'. Those functions 
requres periodically check results and handle timeouts/errors 
(oftenly cleanup + restart helps to fix an error). 
Check/Retry/cleanup code duplicated over a lot of core projects.
As examples - heat, tempest, rally, etc and definitelly in many third-party.

I propose to provide common higth-level API for such functions, which uses
'futures' (http://en.wikipedia.org/wiki/Futures_and_promises) as a way to 
present background task. 

Idea is to add to each background-task-starter function a complimentary call, 
that returns 'future' object. E.g.

    create_future = novaclient.servers.create_async(....)
    .....
    vm = create_future.result()

This allows to unify(and optimize) monitoring cycles, retries, etc.
Please found complete BP at 
https://github.com/koder-ua/os_api/blob/master/README.md

#### Введение и обоснование
-------------------------

В novaclient довольно много API вызовов запускают фоновую операцию
на исполнение и возвращают предварительный результат. К таким
функциям относятся те, которые не только модифицируют записи в базе,
но и выполняют действия над объектами, например:

    * создание/удаление сервера
    * создание/удаление тома
    * присоединение/отсоединение тома к серверу
    * бэкап сервера
    * миграция сервера
    * и другие. 

Novaclient не представляет удобных унифицированных способов дождаться 
завершения фоновой операции или установить таймаута на ее 
исполнение (второе - это больше проблема openstack в целом).

Вторая особенность - фоновые операции могут завершиться ошибкой без 
существенных причин (в следствии ошибок в коде). Чаще всего перезапуск 
такой операции приводит к успешному завершению - это важное отличие от 
большинства других API, где ошибка имеет объективные причины, требующие 
устранения перед перезапуском. Повтор же операции, в отличии от исправления 
причин проблемы, может быть автоматизирован.

В итоге этих двух факторов в коде программ, использующих novaclient,
довольно часто встречается код выполняющий ожидания завершения
фоновой операции, и очистку и перезапуск в случае ошибки или таймаута:

``(TODO: я точно знаю про tempest, heat, cfn-tools, rally. нужно найти ссылки на код)``

```python
for i in range(TRY_COUNT):
    obj = client.create_object()

    for i in range(COUNTER):
        time.sleep(TIMEOUT)
        obj = client.get(obj)
        if obj.state in ('active', 'error'):
            break

    if obj.state == 'active':
        break

    novaclient.servers.delete(vm)
    # тут может идти похожий цикл для удаления
    # поскольку удаление тоже происходит в фоне

obj = client.get(obj)
if obj.state != 'active':
    raise SomeError("Can't create ......")

```

Смысл нового API состоит в унификации подобного кода и предоставлении
удобного и общего способа для мониторинга и перезапуска фоновых операций.
Фактически текущий API напоминает UDP - задача надстроить над ним подобие
TCP.

** API не ставит своей целью построение асинхронного варианта novaclient,
позволяющего параллельно исполнять множество HTTP запросов к openstack API
(эта задача решается с помощью gevent и подобных библиотек). **

#### Описание API
-----------------

Предлагается добавить ко всем функциям, запускающим фоновые операции,
комплиментарные вызовы с почти тем же набором параметров и немного
измененным именем (например с добавлением постфикса _async), которые
возвращают Future (http://en.wikipedia.org/wiki/Futures_and_promises).

Future является стандартным способом обработки фоновых операций и
конкурентности в современных API
(http://en.wikipedia.org/wiki/Futures_and_promises#List_of_implementations).
Важным отличием от модели легковесных потоков(erlang, gevent,
stackless-python) и библиотек типа asyncio
(https://docs.python.org/3/library/asyncio.html)
является возможность обработки множества фоновых операций из одного потока
исполнения.

В python future реализуются стандартным модулем concurrent.future
(https://docs.python.org/3/library/concurrent.futures.html) для 3.X
или его бэкпортом для 2.X - futures (https://pypi.python.org/pypi/futures).

Объект-Future имеет следующие важные методы:

    * done():bool - неблокирующий вызов, проверяет, что результат готов
    * result(timeout=None):object - блокирующий (с тайм аутом) вызов, ожидающий
      готовности future и возвращающий результат или выбрасывающий исключение
      если операция завершилась ошибкой
    * add_done_callback(callback):None - асинхронно вызывает функцию, когда
      future завершится

Пример из введения переписанный на future выглядит так (без автоматических
перезапусков):

```python
for i in range(TRY_COUNT):
    try:
        future_obj = client.create_object_async()
        obj = future_obj.result(TIMEOUT2)
        break
    except (TimeoutError, ObjectCreationError):
        client.delete_async(future_obj.sync_res.id).result()
```

Дополнительно поле sync_res у future содержит результат вызова комплиментарной
стандартной функции client.create_object. Дополнительным параметром для
XXX_async может быть тайм аут выполнения.

Методы вида XXX_async_r дополнительно предоставляют возможность повтора
в случае тайм аута или ошибки. С их использованием указанный код
превращается в одну строку:

```python
res = client.create_object_async_r(try_count=TRY_COUNT, tout=TIMEOUT2).result()
```

Future API, как и стандартный novaclient, позволяет запустить из одного потока
множество операций и выполнять другую работу в том же потоке:

```python
    vm1_future = client.create_object_async_r(...)
    vm2_future = client.create_object_async_r(...)

    # do some other work here

    vm1 = vm1_future.result()
    vm2 = vm2_future.result()
```

На текущий момент POC версия API доступна на https://github.com/koder-ua/os_api,
в ней реализовано создание/удаление серверов.

#### Особенности реализации
---------------------------

Поддержка мониторинга фоновых операций реализована стандартным образом -
через дополнительный поток, который периодически опрашивает openstack о
состоянии требуемых ресурсов. Данные в фоновый поток поступают через очередь
(Queue.Queue) от xxx_async и xxx_async_r функций. При отсутствии мониторимых
ресурсов опрос openstack прекращается.

Есть возможность реализовать API в общем виде, определив для каждой функции
с фоновым исполнением пару функция-проверки/функция-отката, но для такого API
будут недоступны оптимизации за счет получения состояния многих объектов
одним запросом.

#### Комментарии и дополнения
-----------------------------

  * Расширенные варианты future позволяют "присоединять" в future асинхронные
    функции обратного вызова
    (например в scala -
    http://docs.scala-lang.org/overviews/core/futures.html#functional-composition-and-for-comprehensions)
    получая новые future:

    ```python
    vm_future = client.create_object_async_r(...)

    vm_future = vm_future.next(lambda vm: vm.associate_ip(ip))
    vm_future = vm_future.next(lambda vm: vm.attach_volume(vol))

    ```
    В futures соответствующая функциональность не реализована и не
    рассматривается в этом документе.

  * Модуль зависит от concurrent.future но необходим только 
    класс Future, который легко можно реализовать отдельно.
 
