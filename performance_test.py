#!/usr/bin/env python3
"""
Performance Test Script for BlurViewer
Сравнение производительности оригинальной и оптимизированной версий
"""

import time
import sys
import os
from pathlib import Path
import psutil
import subprocess
from typing import List, Dict, Tuple

def get_memory_usage() -> float:
    """Получить текущее использование памяти в МБ"""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024

def get_cpu_usage() -> float:
    """Получить текущее использование CPU в %"""
    return psutil.cpu_percent(interval=0.1)

def find_test_images(directory: str, max_count: int = 10) -> List[str]:
    """Найти тестовые изображения в директории"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff', '.tif'}
    image_files = []
    
    try:
        for file_path in Path(directory).iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                image_files.append(str(file_path))
                if len(image_files) >= max_count:
                    break
    except Exception as e:
        print(f"Ошибка при поиске изображений: {e}")
    
    return image_files

def run_performance_test(script_path: str, test_images: List[str]) -> Dict[str, float]:
    """Запустить тест производительности"""
    print(f"\n🧪 Тестирование: {script_path}")
    
    results = {
        'startup_time': 0.0,
        'memory_usage': 0.0,
        'cpu_usage': 0.0,
        'navigation_time': 0.0
    }
    
    try:
        # Измеряем время запуска
        start_time = time.time()
        
        # Запускаем процесс
        process = subprocess.Popen([
            sys.executable, script_path, test_images[0] if test_images else ""
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Ждем немного для инициализации
        time.sleep(2)
        
        # Измеряем использование ресурсов
        try:
            proc = psutil.Process(process.pid)
            results['memory_usage'] = proc.memory_info().rss / 1024 / 1024
            results['cpu_usage'] = proc.cpu_percent(interval=0.5)
        except psutil.NoSuchProcess:
            pass
        
        # Завершаем процесс
        process.terminate()
        process.wait(timeout=5)
        
        results['startup_time'] = time.time() - start_time
        
    except Exception as e:
        print(f"Ошибка при тестировании {script_path}: {e}")
    
    return results

def print_results(original_results: Dict[str, float], optimized_results: Dict[str, float]):
    """Вывести результаты сравнения"""
    print("\n" + "="*60)
    print("📊 РЕЗУЛЬТАТЫ СРАВНЕНИЯ ПРОИЗВОДИТЕЛЬНОСТИ")
    print("="*60)
    
    metrics = {
        'startup_time': ('Время запуска (с)', 'меньше лучше'),
        'memory_usage': ('Использование памяти (МБ)', 'меньше лучше'),
        'cpu_usage': ('Использование CPU (%)', 'меньше лучше')
    }
    
    for metric, (name, description) in metrics.items():
        original_val = original_results.get(metric, 0)
        optimized_val = optimized_results.get(metric, 0)
        
        if original_val > 0 and optimized_val > 0:
            improvement = ((original_val - optimized_val) / original_val) * 100
            status = "✅ УЛУЧШЕНИЕ" if improvement > 0 else "❌ УХУДШЕНИЕ"
            
            print(f"\n{name}:")
            print(f"  Оригинальная версия: {original_val:.2f}")
            print(f"  Оптимизированная версия: {optimized_val:.2f}")
            print(f"  Изменение: {improvement:+.1f}% {status}")
        else:
            print(f"\n{name}: Данные недоступны")

def main():
    """Основная функция тестирования"""
    print("🚀 ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ BLURVIEWER")
    print("="*50)
    
    # Проверяем наличие файлов
    original_script = "BlurViewer.py"
    optimized_script = "BlurViewer_Optimized.py"
    
    if not os.path.exists(original_script):
        print(f"❌ Файл {original_script} не найден!")
        return
    
    if not os.path.exists(optimized_script):
        print(f"❌ Файл {optimized_script} не найден!")
        return
    
    # Ищем тестовые изображения
    test_directory = input("Введите путь к папке с изображениями (или нажмите Enter для пропуска): ").strip()
    
    test_images = []
    if test_directory and os.path.exists(test_directory):
        test_images = find_test_images(test_directory, max_count=5)
        print(f"Найдено {len(test_images)} тестовых изображений")
    else:
        print("Тестирование без изображений")
    
    # Запускаем тесты
    print("\n🔍 Запуск тестов производительности...")
    
    original_results = run_performance_test(original_script, test_images)
    optimized_results = run_performance_test(optimized_script, test_images)
    
    # Выводим результаты
    print_results(original_results, optimized_results)
    
    # Рекомендации
    print("\n" + "="*60)
    print("💡 РЕКОМЕНДАЦИИ")
    print("="*60)
    
    if optimized_results.get('memory_usage', 0) > original_results.get('memory_usage', 0):
        print("⚠️  Оптимизированная версия использует больше памяти из-за кэширования")
        print("   Это нормально для улучшения производительности навигации")
    
    if optimized_results.get('startup_time', 0) < original_results.get('startup_time', 0):
        print("✅ Оптимизированная версия запускается быстрее")
    
    print("\n📋 Для полного тестирования:")
    print("1. Установите зависимости: pip install -r requirements_optimized.txt")
    print("2. Протестируйте навигацию между изображениями")
    print("3. Проверьте загрузку различных форматов файлов")
    print("4. Оцените плавность анимаций")

if __name__ == "__main__":
    main()