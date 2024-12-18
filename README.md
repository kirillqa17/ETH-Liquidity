Установка и настройка  
1. Установите зависимости и первое подтверждение транзакции
Для работы скрипта вам потребуется Python 3.8 или выше. Установите все необходимые зависимости, выполнив следующую команду:  

pip install -r requirements.txt  

2. Создайте файл wallets.txt  
Добавьте приватные ключи кошельков в файл wallets.txt.  
Пример содержимого файла:  

<PRIVATE_KEY_1>  
<PRIVATE_KEY_2>  
  
Если ключ зашифрован (Base64):

<ENCRYPTED_PRIVATE_KEY_1>  
<ENCRYPTED_PRIVATE_KEY_2>  
Если ключи зашифрованы, программа запросит пароль при запуске.  

3. Настройте .env файл  
Если позиция уже есть в пуле, то необходимо ввести нижнюю и верхнюю границы цены в .env.
Так же необходимо ввести AMOUNT0 для автоматической ребалансировки.
Замените все подписанные переменные для сети Base или Mainnet.  
Убедитесь, что у вас есть доступ к контракту по адресу POSITION_MANAGER_ADDRESS и ABI в указанном пути.  

4. Запустите программу  
Для запуска программы выполните:  

python main.py  

В соответсвенной директории

Функционал  
Обработка кошельков:  
Скрипт поддерживает как незашифрованные, так и зашифрованные приватные ключи. При использовании зашифрованных ключей требуется ввод пароля.  

Автоматическая ребалансировка:  
Программа проверяет текущую цену ETH в диапазоне и автоматически удаляет/добавляет ликвидность, если цена выходит за установленные пороги.  

Ручной ввод ликвидности:  
Если ликвидность отсутствует, пользователь может ввести значение amount0 (WETH) вручную.  

Логи:  
Логи для каждого кошелька сохраняются в отдельные файлы в папке, указанной в LOG_FOLDER.  

Возможные ошибки  
Проблема:  
Файл 'wallets.txt' пуст. Добавьте кошельки в файл.  
Решение:  
Убедитесь, что файл wallets.txt содержит хотя бы один приватный ключ.  

Проблема:
ABI Not Found!
Found 1 element(s) named `positions` that accept 1 argument(s).
The provided arguments are not valid.
Решение:
Если это Ваша первая позиция на данном кошельке, то не обращайте внимания.