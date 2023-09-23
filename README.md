Проект Foodgram - социальная сеть для рецептов
Тут можно публиковать свои рецепты блюд. Подписываться на других пользователей. Добавлять понравившияся рецепты в избранное. Так же можно формировать список покупок для определённого рецепта.

---Как запустить проект локально с помощью Doker:
1)Клонировать репозиторий и перейти в него в терминале:

2)Перейти в директорию с настройками Docker-compose:
cd foodgram-project-react/infra/

3)Создать файл .env и заполнить его:

SECRET_KEY=*Секретный ключ Django*
DEBUG=*False для прода и True для тестов*
ALLOWED_HOSTS=*Список разрешенных хостов*
DB_NAME=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432

4) Запустите образы из файла Docker-compose:

docker-compose up -d --build

5) Примените миграции:

docker-compose exec backend python manage.py migrate

6)Соберите статику:

docker-compose exec backend python manage.py collectstatic --no-input

7) Заполнить базу данными из копии:

docker-compose exec backend python manage.py load_csv_data

8) Создайте суперпользователя:

docker-compose exec backend python manage.py createsuperuser