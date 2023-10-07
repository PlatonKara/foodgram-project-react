import csv
import datetime

from django.core.management import BaseCommand

from recipes.models import Ingredients, Tags

csv_files = {
    Tags: 'tags.csv',
    Ingredients: 'ingredients.csv'
}

fields = {
    Tags: ('name', 'color', 'slug'),
    Ingredients: ('name', 'measurement_unit')
}


class Command(BaseCommand):
    help = ('Загрузка data из data/*.csv.'
            'Запуск: python manage.py load_csv_data.')

    def handle(self, *args, **options):
        print('Старт импорта')
        start_time = datetime.datetime.now()

        try:
            for model, file in csv_files.items():
                to_create = []
                with open(f'../backend/data/{file}', encoding='utf-8') as f:
                    reader = csv.DictReader(f, delimiter=',')
                    for row in reader:
                        if model in fields and len(fields[model]) == 3:
                            row[fields[model][2]] = row.pop(fields[model][0])
                        to_create.append(model(**row))

                model.objects.bulk_create(to_create)
                print(f'{len(to_create)}'
                      f'записей загружено в таблицу {model.__name__}')

            print(f'агрузка данных завершена за'
                  f'{(datetime.datetime.now() - start_time).total_seconds()}'
                  f'сек.')

        except Exception as error:
            print(f'Сбой в работе импорта: {error}.')

        finally:
            print('Завершена работа импорта.')
