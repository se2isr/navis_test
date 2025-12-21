// JavaScript для улучшения админки концептов второго уровня
// Совместимость с Safari

(function() {
    'use strict';
    
    // Используем vanilla JavaScript для лучшей совместимости с Safari
    let initAttempts = 0;
    const maxAttempts = 10;
    
    document.addEventListener('DOMContentLoaded', function() {
        console.log('=== DOMContentLoaded в concept_level2_custom.js ===');
        // Ждем, пока Django загрузит все свои скрипты
        setTimeout(initializeConceptForm, 500);
    });
    
    // Также пробуем при полной загрузке страницы
    window.addEventListener('load', function() {
        console.log('=== Window.load в concept_level2_custom.js ===');
        setTimeout(initializeConceptForm, 100);
    });
    
    function initializeConceptForm() {
        initAttempts++;
        console.log('Попытка инициализации #' + initAttempts);
        
        const root_lv2_field = document.getElementById('id_root_lv2');
        const kind_field = document.getElementById('id_kind');
        
        console.log('root_lv2_field:', root_lv2_field);
        console.log('kind_field:', kind_field);
        
        if (!root_lv2_field || !kind_field) {
            if (initAttempts < maxAttempts) {
                console.log('Поля не найдены, повторная попытка через 500мс (попытка ' + initAttempts + '/' + maxAttempts + ')');
                setTimeout(initializeConceptForm, 500);
            } else {
                console.error('Не удалось найти поля после ' + maxAttempts + ' попыток');
            }
            return;
        }
        
        console.log('=== Инициализация формы концептов уровня 2 ===');
        
        // ===================================
        // 1. Создаем маппинг id -> kind из options
        // ===================================
        const conceptKindMap = {};
        const options = root_lv2_field.querySelectorAll('option');
        
        options.forEach(function(option) {
            const text = option.textContent.trim();
            // Ищем паттерн "[O]", "[P]", "[A]" или "[I]" в начале текста
            const match = text.match(/^\[([OPAI])\]/);
            if (match && option.value) {
                conceptKindMap[option.value] = match[1];
                console.log('Найден концепт:', option.value, '→', match[1]);
            }
        });
        
        console.log('Маппинг kind:', conceptKindMap);
        
        // ===================================
        // 2. Функция для обновления kind
        // ===================================
        function updateKind() {
            const selectedId = root_lv2_field.value;
            console.log('Выбран родитель:', selectedId);
            
            if (selectedId && conceptKindMap[selectedId]) {
                const selectedKind = conceptKindMap[selectedId];
                console.log('Устанавливаем kind:', selectedKind);
                
                kind_field.value = selectedKind;
                kind_field.style.backgroundColor = '#e8f5e9';
                kind_field.readOnly = true;
            } else if (!selectedId) {
                kind_field.style.backgroundColor = '';
                kind_field.readOnly = false;
            }
        }
        
        // Обновляем при изменении root_lv2
        root_lv2_field.addEventListener('change', updateKind);
        
        // Обновляем при загрузке страницы, если root_lv2 уже выбран
        if (root_lv2_field.value) {
            updateKind();
        }
        
        
        // ===================================
        // 3. Улучшенное отображение в select (делаем ДО клонирования)
        // ===================================
        options.forEach(function(option) {
            const text = option.textContent.trim();
            const match = text.match(/^\[([OPAI])\]\s*(.+)$/);
            if (match) {
                const kind = match[1];
                const label = match[2];
                
                // Добавляем эмодзи для визуального выделения
                let icon = '';
                switch(kind) {
                    case 'O': icon = '🔵'; break;
                    case 'P': icon = '🟠'; break;
                    case 'A': icon = '⚪'; break;
                    case 'I': icon = '🟢'; break;
                }
                
                option.textContent = icon + ' [' + kind + '] ' + label;
            }
        });
        
        console.log('Эмодзи добавлены к options');
        
        
        // ===================================
        // 4. Кнопки фильтрации по Kind
        // ===================================
        const rootLv2Row = document.querySelector('.field-root_lv2');
        
        if (rootLv2Row) {
            // ВАЖНО: Проверяем, что кнопки еще не добавлены
            if (document.querySelector('.concept-kind-filter')) {
                console.log('Кнопки фильтрации уже существуют, пропускаем');
                return;
            }
            
            console.log('Добавляем кнопки фильтрации');
            
            // Создаем контейнер для кнопок фильтрации
            const filterButtons = document.createElement('div');
            filterButtons.className = 'concept-kind-filter';
            
            const kinds = [
                { code: 'all', label: 'Все', color: '#e9ecef', textColor: '#495057' },
                { code: 'O', label: 'Объект', color: '#60a5fa', textColor: 'white' },
                { code: 'P', label: 'Процесс', color: '#f97316', textColor: 'white' },
                { code: 'A', label: 'Актор', color: '#64748b', textColor: 'white' },
                { code: 'I', label: 'Информация', color: '#4ade80', textColor: 'white' }
            ];
            
            // Сохраняем все опции ПОСЛЕ добавления эмодзи
            const allOptions = Array.from(root_lv2_field.querySelectorAll('option')).map(opt => opt.cloneNode(true));
            console.log('Сохранено опций:', allOptions.length);
            
            // Создаем кнопки
            kinds.forEach(function(kind) {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'filter-btn';
                button.textContent = kind.code === 'all' ? kind.label : kind.code;
                button.setAttribute('data-kind', kind.code);
                button.style.background = kind.color;
                button.style.color = kind.textColor;
                button.style.borderColor = kind.color;
                
                if (kind.code === 'all') {
                    button.classList.add('active');
                }
                
                button.setAttribute('title', kind.label);
                
                // Обработчик клика
                button.addEventListener('click', function(e) {
                    e.preventDefault();
                    
                    // Убираем active со всех кнопок
                    filterButtons.querySelectorAll('.filter-btn').forEach(function(btn) {
                        btn.classList.remove('active');
                    });
                    
                    // Добавляем active на текущую
                    button.classList.add('active');
                    
                    // Фильтруем
                    filterConcepts(kind.code);
                });
                
                filterButtons.appendChild(button);
            });
            
            // Функция фильтрации
            function filterConcepts(kindCode) {
                console.log('Фильтрация по:', kindCode);
                
                const currentValue = root_lv2_field.value;
                let addedCount = 0;
                
                // Очищаем select
                root_lv2_field.innerHTML = '';
                
                if (kindCode === 'all') {
                    // Показываем все опции (включая пустую)
                    allOptions.forEach(function(opt) {
                        root_lv2_field.appendChild(opt.cloneNode(true));
                        addedCount++;
                    });
                } else {
                    // Фильтруем по kind
                    allOptions.forEach(function(opt) {
                        const text = opt.textContent.trim();
                        console.log('Проверка опции:', text, 'для kind:', kindCode);
                        
                        // Ищем паттерн [O], [P], [A] или [I] в тексте
                        const kindMatch = text.match(/\[([OPAI])\]/);
                        
                        if (kindMatch && kindMatch[1] === kindCode) {
                            console.log('✓ Добавлена:', text);
                            root_lv2_field.appendChild(opt.cloneNode(true));
                            addedCount++;
                        }
                    });
                }
                
                console.log('Добавлено опций:', addedCount);
                
                // Восстанавливаем выбранное значение, если оно есть
                if (currentValue) {
                    const matchingOption = root_lv2_field.querySelector('option[value="' + currentValue + '"]');
                    if (matchingOption) {
                        root_lv2_field.value = currentValue;
                        console.log('Восстановлено выбранное значение:', currentValue);
                    }
                }
            }
            
            // Вставляем кнопки перед полем root_lv2
            const fieldBox = rootLv2Row.querySelector('.field-box') || rootLv2Row.querySelector('div');
            if (fieldBox) {
                fieldBox.insertBefore(filterButtons, fieldBox.firstChild);
                console.log('Кнопки добавлены');
            } else {
                console.log('field-box не найден');
            }
        } else {
            console.log('root_lv2 row не найден');
        }
        
        console.log('Инициализация завершена');
    }
    
})();
