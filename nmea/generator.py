# nmea/generator.py - Генерация NMEA-строк с контрольной суммой

class NMEAGenerator:
    """
    Генератор NMEA-строк формата 0183.
    
    Поддерживаемые сообщения:
    - $GPRMC: Recommended Minimum Navigation Information
    - $GPVTG: Course Over Ground and Ground Speed
    - $HDT:  Heading True
    """
    
    @staticmethod
    def calculate_checksum(sentence_body: str) -> str:
        """
        Вычисляет XOR-контрольную сумму NMEA.
        
        Args:
            sentence_body: Тело сообщения без $ и * (например: "GPRMC,123519,A...")
            
        Returns:
            Двухзначная HEX-строка (например: "6A")
        """
        checksum = 0
        for char in sentence_body:
            checksum ^= ord(char)
        return f"{checksum:02X}"
    
    @staticmethod
    def decimal_to_nmea_lat(value: float) -> tuple:
        """
        Конвертирует десятичную широту в формат NMEA (DDMM.MMMM).
        
        Args:
            value: Широта в десятичных градусах (например: 55.751244)
            
        Returns:
            Кортеж (строка_широты, направление): ("5545.0746", "N")
        """
        degrees = int(abs(value))
        minutes = (abs(value) - degrees) * 60
        nmea_string = f"{degrees:02d}{minutes:07.4f}"
        direction = "N" if value >= 0 else "S"
        return nmea_string, direction
    
    @staticmethod
    def decimal_to_nmea_lon(value: float) -> tuple:
        """
        Конвертирует десятичную долготу в формат NMEA (DDDMM.MMMM).
        
        Args:
            value: Долгота в десятичных градусах (например: 37.618423)
            
        Returns:
            Кортеж (строка_долготы, направление): ("03737.1054", "E")
        """
        degrees = int(abs(value))
        minutes = (abs(value) - degrees) * 60
        nmea_string = f"{degrees:03d}{minutes:07.4f}"
        direction = "E" if value >= 0 else "W"
        return nmea_string, direction
    
    @staticmethod
    def generate_gprmc(lat: float, lon: float, course: float, 
                       speed: float, timestamp=None) -> str:
        """
        Генерирует NMEA-строку $GPRMC (Recommended Minimum Navigation Information).
        
        Формат: $GPRMC,time,status,lat,NS,lon,EW,speed,course,date,magvar,E/W*checksum
        
        Args:
            lat: Широта в десятичных градусах
            lon: Долгота в десятичных градусах
            course: Курс в градусах (0-360)
            speed: Скорость в узлах
            timestamp: datetime объект (если None, используется текущее время UTC)
            
        Returns:
            Полная NMEA-строка с checksum
        """
        from datetime import datetime, timezone
        
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        # Время в формате HHMMSS
        time_str = timestamp.strftime("%H%M%S")
        
        # Дата в формате DDMMYY
        date_str = timestamp.strftime("%d%m%y")
        
        # Конвертация координат
        lat_nmea, lat_dir = NMEAGenerator.decimal_to_nmea_lat(lat)
        lon_nmea, lon_dir = NMEAGenerator.decimal_to_nmea_lon(lon)
        
        # Собираем тело сообщения (без $ и *)
        body = f"GPRMC,{time_str},A,{lat_nmea},{lat_dir},{lon_nmea},{lon_dir},{speed:.1f},{course:.1f},{date_str},,E"
        
        # Вычисляем checksum
        checksum = NMEAGenerator.calculate_checksum(body)
        
        # Возвращаем полную строку
        return f"${body}*{checksum}"
    
    @staticmethod
    def generate_gpvtg(course: float, speed: float) -> str:
        """
        Генерирует NMEA-строку $GPVTG (Course Over Ground and Ground Speed).
        
        Формат: $GPVTG,course_true,T,course_mag,M,speed_knots,N,speed_kmh,K*checksum
        
        Args:
            course: Курс в градусах
            speed: Скорость в узлах
            
        Returns:
            Полная NMEA-строка с checksum
        """
        # Конвертация скорости: узлы -> км/ч
        speed_kmh = speed * 1.852
        
        body = f"GPVTG,{course:.1f},T,,M,{speed:.1f},N,{speed_kmh:.1f},K"
        checksum = NMEAGenerator.calculate_checksum(body)
        
        return f"${body}*{checksum}"
    
    @staticmethod
    def generate_hdt(heading: float) -> str:
        """
        Генерирует NMEA-строку $HDT (Heading True).
        
        Формат: $HDT,heading,T*checksum
        
        Args:
            heading: Истинный курс в градусах
            
        Returns:
            Полная NMEA-строка с checksum
        """
        body = f"HDT,{heading:.1f},T"
        checksum = NMEAGenerator.calculate_checksum(body)
        
        return f"${body}*{checksum}"