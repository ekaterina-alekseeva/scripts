# 0. импортировать нужные библиотеки

from brownie import *
from brownie import BrownieSafe

from utils.config import contracts # для использования метода getmembers
"""
# 1. получить адреса пользователей
def get_user_addresses():
    return hash_consensus.getMembers() #todo: скорее всего неправильно, исправить

user_addresses = get_user_addresses()
print('Адреса пользоватeлей: ', user_addresses)

# 2. определить баланс эфира пользователей

print('Баланс пользователей:')
for item in user_addresses:
    print(item, ':', item.balance())

# отобрать пользователей с балансом меньше чем 1 эфир
user_addresses_filtered = list(filter(lambda x: x.balance() < '1 ether', user_addresses))

print('Список пользователей c балансом меньше 1: ')
for item in user_addresses_filtered:
    print(item, ':', item.balance())

# получить данные кошелька, с которого будет выполнена транзакция
safe = BrownieSafe('ychad.eth') # todo: изменить имя сети, возможно не нужно
multisig_account = safe.account() # todo: указать адрес кошелька, с которого будет проводиться транзакция, исправить

# 3. проверить, что на счету достаточно баланса для проведения начисления, если нет - вернуть ошибку
def get_total_balance():
    return multisig_account.balance()

current_balance = get_total_balance()
accrual = ['1 ether'-item.balance() for item in user_addresses_filtered]
total_accrual = sum(accrual)
print('Нужно эфира для начисления: ', Wei(total_accrual).to("ether"))

try:
    if total_accrual > current_balance :
        raise Exception(f"Недостаточно средств для начисления, баланс - {current_balance}, требуется - {total_accrual}.")

    # 3. собрать транзакцию для сейфа, список "адрес получателя, начисления, адрес отправителя"

    txs = [(item, '1 ether' - item.balance(), {'from':multisig_account}) for item in user_addresses_filtered]

    # 4. получить подтверждение у пользователя в консоли запуска скрипта
    print('Хотите выполнить начисление?')
    attempts = 0
    while True and attempts < 3:
        print('Введите y или n:')

        answer = input()
        if answer == 'y':
            print('Выполняем транзакцию.')

            # 5. выполнить транзакцию
            safe_tx = safe.multisend_from_receipts(txs) # отправка нескольким получателям
            safe.preview(safe_tx) # предпросмотр транзакции
            safe.post_transaction(safe_tx) # отправка транзакции

            break
        elif answer == 'n':
            print('Транзакция отменена.')
            break
        else:
            print('Некорректный ответ.')

        attempts += 1
        if attempts==3:
            print('Превышено количество попыток ввода.')

except Exception as e:
    print(f"Сообщение об ошибке: {e}")
    print("Завершаем работу скрипта.")
"""
print('hello, world')
print(hash_consensus.getMembers())
