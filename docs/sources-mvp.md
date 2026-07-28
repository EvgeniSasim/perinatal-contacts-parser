# Источники данных (реальные)

## Что используется сейчас

| Источник | Тип доступа | Ключ | Что даёт | Статус |
|----------|-------------|------|----------|--------|
| **OpenStreetMap / Nominatim** | публичный API | не нужен | название, адрес, город | ✅ |
| **Реестр официальных сайтов** | HTTP HTML | не нужен | телефон, email | ✅ |
| **OrgPage** perinatalnye-tsentry | HTML каталог | не нужен | ПЦ по РФ + телефоны | ✅ |
| **MedAdvisor** роддома/ПЦ | HTML+JSON в разметке | не нужен | клиники по регионам | ✅ |
| **КП** рейтинг роддомов | HTML статья | не нужен | топ с адресом/телефоном | ✅ |
| **Zdrav.expert** | HTML статья | не нужен | упоминания ПЦ | ✅ |
| **RussiaMedTravel** акушерство | HTML каталог | не нужен | организации Минздрава | ✅ |
| **Vademecum** рейтинг 2017 | HTML таблица | не нужен | ПЦ + город | ✅ |
| **Минздрав Мурманской обл. PDF** | PDF перечень | не нужен | ЭКО/ПЦ с адресами | ✅ |
| **Seed CSV** | файл | не нужен | снимок сборки | ✅ |
| **2GIS Places API** | API | `DGIS_API_KEY` | контакты | код готов |
| **Яндекс Organizations API** | API | `YANDEX_MAPS_API_KEY` | контакты | код готов |

## Каталоги

- https://www.orgpage.ru/rossiya/perinatalnye-tsentry/
- https://medadvisor.ru/russia/clinics/rodilnye-doma-i-perinatalnye-tsentry
- https://www.kp.ru/russia/lechenie-v-rossii/roddoma/
- https://zdrav.expert/…Перинатальные_центры_в_России
- https://russiamedtravel.ru/catalog/akusherstvo/
- https://minzdrav.gov-murman.ru/activities/akusherstvo/doc/list.pdf
- https://vademec.ru/news/2017/09/15/predstavlen-reyting-perinatalnykh-tsentrov/

## Ограничения robots.txt

- **MedAdvisor**: `*?page=*` запрещён — берём первые страницы регионов без `?page=`.
- **OrgPage**: `/*?` запрещён — пагинация path `/2/` и региональные URL.
- HTML `2gis.ru` / `yandex.ru/maps` не скрапим — только официальные API.

## Запуск

```bash
PYTHONPATH=apps/api python scripts/crawl_real.py --source catalogs
PYTHONPATH=apps/api python scripts/crawl_real.py --source all_free
```
