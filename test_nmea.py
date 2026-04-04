# test_nmea.py - Тесты для NMEA генератора

from nmea.generator import NMEAGenerator

def test_checksum():
    """Проверка расчёта контрольной суммы"""
    # Известная тестовая строка
    body = "GPRMC,081836,A,3751.65,S,14507.36,E,000.0,360.0,130998,011.3,E"
    checksum = NMEAGenerator.calculate_checksum(body)
    print(f"Checksum для тестовой строки: {checksum}")
    # Для этой строки известный checksum = 62
    assert checksum == "62", f"Ожидалось 62, получилось {checksum}"
    print("✅ Checksum тест пройден")

def test_gprmc_format():
    """Проверка формата GPRMC"""
    sentence = NMEAGenerator.generate_gprmc(55.751244, 37.618423, 180.0, 10.5)
    
    print(f"\nСгенерированная строка GPRMC:")
    print(sentence)
    
    # Проверки
    assert sentence.startswith("$GPRMC"), "Должно начинаться с $GPRMC"
    assert "*" in sentence, "Должен быть символ *"
    assert len(sentence.split("*")[1]) == 2, "Checksum должен быть 2 символа"
    
    print("✅ Формат GPRMC корректен")

def test_coordinate_conversion():
    """Проверка конвертации координат"""
    lat_nmea, lat_dir = NMEAGenerator.decimal_to_nmea_lat(55.751244)
    lon_nmea, lon_dir = NMEAGenerator.decimal_to_nmea_lon(37.618423)
    
    print(f"\nШирота: {lat_nmea} {lat_dir}")
    print(f"Долгота: {lon_nmea} {lon_dir}")
    
    assert lat_dir == "N", "Москва в северном полушарии"
    assert lon_dir == "E", "Москва в восточном полушарии"
    
    print("✅ Конвертация координат корректна")

if __name__ == "__main__":
    print("🧪 Запуск тестов NMEA генератора...\n")
    print("=" * 50)
    
    test_checksum()
    test_gprmc_format()
    test_coordinate_conversion()
    
    print("=" * 50)
    print("🎉 Все тесты пройдены!")