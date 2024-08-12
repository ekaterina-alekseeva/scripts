# 0. импортировать нужные библиотеки

from brownie import *
from brownie_safe import BrownieSafe
from brownie.network.gas.strategies import LinearScalingStrategy

# from utils.config import contracts # для использования метода getmembers

def get_user_addresses():
    # сформировать список аккаунтов пользователей, которым должен быть переведен эфир

    # заменить при переходе на боевую сеть
    '''
    consensus_contract = contracts.hash_consensus_for_validators_exit_bus_oracle #todo: скорее всего неправильно, исправить
    members = consensus_contract.getMembers()
    '''
    
    members = [accounts[1], accounts[2], accounts[3]]
    return members

def get_wallet_address():
    # получить адрес кошелька, с которого будет выполнен перевод
    return accounts[9]

def get_total_balance():
    # получить баланс кошелька, с которого будет выполнен перевод

    # return multisig_account.balance()

    wallet_address = get_wallet_address()
    return wallet_address.balance()

def send_ether(lst):
    # перевести эфир пользователям согласно заданным параметрам
    for item in lst:
        gas_strategy = LinearScalingStrategy("10 gwei", "50 gwei", 1.1)
        "tx = user_addresses[0].transfer(user_addresses[1], 10**18, gas_price=gas_strategy)"
        tx = accounts[item[0]].transfer(accounts[item[1]], item[2] * 10 ** 18, gas_price=gas_strategy)
        chain.mine()

def main():

    # пример использования safe
    # safe = BrownieSafe('ychad.eth')

    # dai = safe.contract('0x6B175474E89094C44Da98b954EedeAC495271d0F')
    # vault = safe.contract('0x19D3364A399d251E894aC732651be8B0E4e85001')

    # amount = dai.balanceOf(safe.account)
    # dai.approve(vault, amount)
    # vault.deposit(amount)

    # safe_tx = safe.multisend_from_receipts()
    # safe.preview(safe_tx)
    # safe.post_transaction(safe_tx)

    # ВОПРОС: непонятно, по какому принципу выбираются контаркты в примере выше, какие контракты нужно использовать для текущего скрипта?

    # определить safe account, с которого будет выполнен перевод
    # для отладки используется один из доступных на ноде, в проде нужно переключить на боевой и проверить доступность из исопльзуемой сети
    safe = BrownieSafe(accounts[5].address)

    # 0. начислить нужное для тестирования количество эфира
    # send_ether([[0,9,46], [2,9,99.5]])

    # 1. получить адреса пользователей
    user_addresses = get_user_addresses()

    # 2. сформировать словарь с данными: аккаунт, баланс, признак начисления, сумма начисления (в wei)
    info = []
    for item in user_addresses:
        info.append({'account': item, 'balance': item.balance(), 'accrual_flag': item.balance() < '1 ether',
                     'accrual': Wei("1 ether") - Wei(item.balance())})
    '''
    for item in info:
        print(item)
    print()
    '''

    # 3. отобрать пользователей с балансом меньше чем 1 эфир
    info_filtered = list(filter(lambda x: x['accrual_flag'], info))
    '''
    for item in info_filtered:
        print(item)
    '''

    # 4. получить данные кошелька, с которого будет выполнена транзакция
    # safe = BrownieSafe('ychad.eth')
    # multisig_account = safe.account()

    wallet = get_wallet_address()
    '''
    print('Wallet account: ', wallet)
    '''
    
    # 5. проверить, что на счету достаточно баланса для проведения начисления

    current_balance = Wei(wallet.balance()).to('ether')
    total_accrual = Wei(sum(item['accrual'] for item in info_filtered)).to('ether')
    '''
    print(f"Current wallet balance - {current_balance}, total accrual: {total_accrual}")
    '''
    
    # если эфира достаточно - сформировать транзакцию, если недостаточно - вернуть ошибку
    try:
        if total_accrual > current_balance:
            raise Exception(
                f"Недостаточно средств для начисления, баланс - {current_balance}, требуется - {total_accrual}.")

        # 3. подготовить данные для транзакции

        '''
        # создаем массив данных транзакций (для обычных транзакций)
        transactions = [(item['account'], item['accrual'], {'from': wallet}) for item in info_filtered]
        gas_strategy = LinearScalingStrategy("10 gwei", "50 gwei", 1.1)
        '''

        '''
        # Создаем массив для данных транзакций (для safe-транзакции)
        transactions = []
        for recipient in info_filtered:
            # Создаем транзакцию для каждого получателя
            transactions.append({
                'to': recipient['account'],
                'value': recipient['accrual'],
                'data': b'',  # Пустые данные для простого перевода ETH
                'operation': 0  # 0 - CALL, 1 - DELEGATE_CALL
            })
        '''

        # 4. получить подтверждение у пользователя в консоли запуска скрипта
        print('Хотите выполнить начисление?')
        attempts = 0
        while True and attempts < 3:
            print('Введите y или n:')

            answer = input()
            if answer == 'y':
                print('Выполняем транзакцию.')

                # 5. выполнить транзакцию
        
                '''
                # обычная транзакция
                transactions = [
                    item['account'].transfer(wallet, item['accrual'], gas_price=gas_strategy, required_confs=0,
                                             silent=True)
                    for item in info_filtered
                ]
                '''
                
                '''
                # safe-транзакция
                safe_tx = safe.multisend_from_receipts(txs)  # отправка нескольким получателям
                safe.preview(safe_tx)  # предпросмотр транзакции
                safe.post_transaction(safe_tx)  # отправка транзакции
                '''
                
                break
            elif answer == 'n':
                print('Транзакция отменена.')
                break
            else:
                print('Некорректный ответ.')

            attempts += 1
            if attempts == 3:
                print('Превышено количество попыток ввода.')

    except Exception as e:
        print(f"Сообщение об ошибке: {e}")
        print("Завершаем работу скрипта.")
