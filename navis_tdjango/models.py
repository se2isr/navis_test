from django.db import models
from django.utils import timezone


# =========================
# NAVIS CORE (БАЗОВЫЙ СЛОЙ)
# =========================

class Concept(models.Model):
    """
    NAVIS CORE: Универсальный реестр концептов (узлов) онтологии.

    В NAVIS v3 все сущности представляются концептами четырёх верхних классов:
      - O: Object        (материальный объект / физическая система)
      - P: Process       (процесс во времени; событие = частный случай процесса)
      - A: Actor         (актор / субъект действия)
      - I: Information   (информационный объект: метрики, формулы, сценарии, периоды, модели и т.д.)

    Ключевые принципы:
      1) Никаких доменных таблиц "продукт/здание/метрика/сценарий" — всё это Concept.
      2) Иерархия/классификация делается связью Edge с типом RelationType 'is_a'.
      3) Структура "часть-целое" делается связью Edge с типом RelationType 'part_of'.
      4) Атрибуты/характеристики хранятся как I-концепты и привязываются через 'describes' (-?->).

    Пример ключей:
      - Product.Slab
      - Scenario.Base
      - Period.2026
      - Price(Product.Slab, Scenario.Base, Period.2026)
      - Formula.Revenue.Product.Slab.Base.2026
    """

    class Kind(models.TextChoices):
        OBJECT = "O", "Объект (материальный)"
        PROCESS = "P", "Процесс"
        ACTOR = "A", "Актор"
        INFO = "I", "Информация"

    key = models.CharField(
        max_length=500,
        unique=True,
        help_text="Стабильный уникальный ключ концепта (используется в тексте/боте/API), например 'Product.Slab'."
    )
    label = models.CharField(
        max_length=500,
        blank=True,
        help_text="Человекочитаемое имя для UI. Если пусто — будет автоматически равно key."
    )
    kind = models.CharField(
        max_length=1,
        choices=Kind.choices,
        help_text="Верхний класс концепта (O/P/A/I)."
    )
    
    root_lv2 = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children_lv2",
        help_text="Родительский концепт первого уровня (NULL для концептов первого уровня).",
        limit_choices_to={'root_lv2__isnull': True}
    )

    description = models.TextField(
        blank=True,
        help_text="Свободное описание/пояснение (не влияет на вычисления)."
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Технический флаг: активен ли концепт (для UI/фильтрации)."
    )

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "navis_concept"
        verbose_name = "Концепт (уровень 1)"
        verbose_name_plural = "Концепты (уровень 1)"
        indexes = [
            models.Index(fields=["kind"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["root_lv2"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self) -> str:
        # Показываем label, если он есть, иначе key
        display_name = self.label if self.label else self.key
        # Для концептов первого уровня добавляем kind для идентификации
        if self.root_lv2 is None:
            return f"[{self.kind}] {display_name}"
        return display_name


class ConceptLevel2(Concept):
    """
    Proxy-модель для концептов второго уровня (с родителем).
    Используется для отдельного отображения в админке.
    """
    class Meta:
        proxy = True
        verbose_name = "Концепт (уровень 2+)"
        verbose_name_plural = "Концепты (уровень 2+)"


class RelationType(models.Model):
    """
    NAVIS CORE: Типы связей (relation types) как ДАННЫЕ, а не хардкод в коде.

    Требование NAVIS:
      - словарь связей должен быть управляемым и расширяемым без релизов кода.

    Механизм "все связи — разновидности одной верхней связи":
      - есть верхний тип связи: key='relation' (parent=NULL)
      - все остальные типы связей являются его разновидностями (parent -> 'relation')
      - при необходимости можно строить более глубокую иерархию разновидностей связей,
        но "базовыми" для ввода/бота/интерфейса остаются только связи is_base=True, которые можно использовать напрямую.

    Поля:
      - key: каноническое имя типа связи (например 'describes', 'is_a', 'part_of')
      - alias: алиас для текстового ввода (например '-?->', '-@->', '-*->', '-!->')
      - is_base: разрешено ли использовать данный тип связи напрямую пользователями/ботом
    """

    key = models.CharField(
        max_length=100,
        unique=True,
        help_text="Каноническое имя типа связи, например 'describes', 'is_a', 'part_of'."
    )

    alias = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text="Текстовый алиас (оператор) для сообщений, например '-?->'. Может быть пустым для служебных типов связи."
    )

    label = models.CharField(
        max_length=200,
        help_text="Человекочитаемое имя типа связи, например 'Описывает', 'Является', 'Часть'."
    )

    description = models.TextField(
        blank=True,
        help_text="Пояснение смысла типа связи (для справки/документации)."
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
        help_text="Родительский тип связи в иерархии разновидностей связи. Для корневого 'relation' = NULL."
    )

    is_base = models.BooleanField(
        default=False,
        help_text="Если True — тип связи разрешён как базовый оператор для ввода пользователем/ботом и для UI."
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Технический флаг активности типа связи."
    )

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "navis_relation_type"
        indexes = [
            models.Index(fields=["is_base"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self) -> str:
        return f"{self.key} ({self.alias})"


class Edge(models.Model):
    """
    NAVIS CORE: Универсальная таблица связей (edges) между концептами.

    В отличие от Enum-хардкода, тип связи задаётся ссылкой на RelationType (как данные) для управляемости и расширяемости.

    Примеры связей для NAVIS v3:
      - иерархия концептов: Edge(relation_type='is_a')   alias '-@->'
      - часть-целое:        Edge(relation_type='part_of') alias '-*->'
      - "описание":         Edge(relation_type='describes') alias '-?->'
        (в вычислительном режиме это основной оператор для проводки формул/переменных/ролей)

    Важное добавление для кеширования:
      - updated_at: позволяет корректно инвалидировать кеш структуры,
        если связь меняют (а не только создают/удаляют).
    """

    from_concept = models.ForeignKey(
        Concept,
        on_delete=models.CASCADE,
        related_name="out_edges",
        help_text="Исходный концепт (откуда идёт связь)."
    )
    relation_type = models.ForeignKey(
        RelationType,
        on_delete=models.PROTECT,
        related_name="edges",
        help_text="Тип связи (управляется данными, включает алиасы и иерархию)."
    )
    to_concept = models.ForeignKey(
        Concept,
        on_delete=models.CASCADE,
        related_name="in_edges",
        help_text="Целевой концепт (куда указывает связь)."
    )

    weight = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Необязательный технический вес связи (не использовать для доменной семантики)."
    )

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "navis_edge"
        indexes = [
            models.Index(fields=["from_concept", "relation_type"]),
            models.Index(fields=["to_concept", "relation_type"]),
            models.Index(fields=["relation_type"]),
            models.Index(fields=["updated_at"]),
        ]
        # Уникальность (from, type, to) намеренно НЕ ограничиваем:
        # в будущем могут быть параллельные утверждения/контексты/авторы.
        # Ограничения вводятся на уровне "скоупов" (контекстов) поверх core.

    def __str__(self) -> str:
        return f"{self.from_concept_id} -[{self.relation_type.key}]-> {self.to_concept_id}"


class Formula(models.Model):
    """
    NAVIS CORE: Исполняемая формула (выражение) для вычислений, привязанная к концепту.

    Как это устроено в NAVIS:
      - Формула — это I-концепт (Concept.kind='I' и тип I.Formula через is_a), например:
          'I.Formula.Revenue.Product.Slab.Base.2026'
      - Здесь хранится исполняемый текст выражения (language='expr'):
          'PRICE_P * VOLUME'
      - Проводка (какие переменные откуда берутся, что является output) хранится в графе Edge,
        обычно через базовый тип связи 'describes' (-?->), например:
          Formula -?-> I.Role.Output
          Formula -?-> I.Revenue(...)
          Formula -?-> I.Var.PRICE_P
          I.Var.PRICE_P -?-> I.Price(...)
    """

    concept = models.OneToOneField(
        Concept,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="formula",
        help_text="Концепт формулы (обычно kind='I' и типизирован как I.Formula через is_a) для вычислений."
    )
    language = models.CharField(
        max_length=30,
        default="expr",
        help_text="Язык выражения (для MVP: 'expr' — простая арифметика)."
    )
    expression = models.TextField(
        help_text="Текст исполняемого выражения (без присваивания; для MVP: 'PRICE_P * VOLUME')."
    )

    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "navis_formula"
        indexes = [
            models.Index(fields=["language"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self) -> str:
        return f"Formula({self.concept_id}, {self.language}: {self.expression})"


class InfoValue(models.Model):
    """
    NAVIS CORE: Значение (число/текст) для информационного концепта (I-концепта).

    Принцип твоего стандарта:
      - Scenario и Period кодируются в ключе I-концепта (Concept.key),
        поэтому здесь нет отдельных полей scenario_id/period_id.
      - Ключ (concept_id) однозначно идентифицирует "I.Price(Product.Slab, Scenario.Base, Period.2026)".

    Варианты использования:
      - сюда загружаются "листья" (входные данные: цены/объёмы/нормы/ставки),
      - сюда же можно писать результаты вычислений (для MVP: Revenue = Price * Volume),
      - позже можно добавить тех-таблицы InfoResult для истории прогонов без изменения core.
    """

    concept = models.OneToOneField(
        Concept,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="info_value",
        help_text="Информационный концепт (I-концепт), для которого хранится значение."
    )

    value_num = models.DecimalField(
        max_digits=30,
        decimal_places=10,
        null=True,
        blank=True,
        help_text="Числовое значение (для финансов/инженерии; для MVP: Price = 100, Volume = 1000)."
    )
    value_text = models.TextField(
        null=True,
        blank=True,
        help_text="Текстовое значение (если I-концепт не числовой; для MVP: 'USD', 'EUR')."
    )

    unit = models.CharField(
        max_length=50,
        blank=True,
        help_text="Единица измерения (для MVP: 'USD', 'EUR')."
    )

    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "navis_info_value"
        indexes = [
            models.Index(fields=["updated_at"]),
            models.Index(fields=["unit"]),
        ]

    def __str__(self) -> str:
        if self.value_num is not None:
            return f"I.Value({self.concept_id}={self.value_num} {self.unit})"
        return f"I.Value({self.concept_id}={self.value_text})"


# ============================================
# ДОБАВКИ ДЛЯ КЕШИРОВАНИЯ / СТРОГОЙ ТИПИЗАЦИИ
# ============================================

class CalcModel(models.Model):
    """
    TECH+CORE: Реестр вычислительных моделей (сборок) верхнего уровня (для MVP: invest.pnl_cf.v1).

    Зачем нужно уже на "базовом" этапе (для MVP):
      - чтобы не "искать формулы по магии имен" и не строить адские запросы по графу (как в NAVIS v2)
      - модель явно перечисляет блоки, а блоки — явно перечисляют формулы
    """

    model_key = models.CharField(
        max_length=200,
        unique=True,
        help_text="Уникальный ключ модели расчёта (для MVP: 'invest.pnl_cf.v1')."
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "calc_model"
        indexes = [
            models.Index(fields=["model_key"]),
        ]

    def __str__(self) -> str:
        return f"CalcModel({self.model_key})"


class CalcBlock(models.Model):
    """
    TECH+CORE: Крупный вычислительный блок (\"большой кубик\").

    Идея:
      - модель собирается из блоков (CAPEX, Production, UnitCosts, PnL, CashFlow) (для MVP)
      - кеширование/компиляция будет делаться на уровне блоков (для MVP)

    На базовом этапе (для MVP) это нужно, чтобы:
      - явно управлять составом формул,
      - позже кешировать структуру блока независимо от всей модели.
    """

    block_key = models.CharField(
        max_length=200,
        unique=True,
        help_text="Уникальный ключ блока (для MVP: 'CAPEX', 'Production', 'UnitCosts', 'PnL', 'CashFlow')."
    )
    description = models.TextField(blank=True)

    class Meta:
        db_table = "calc_block"
        indexes = [
            models.Index(fields=["block_key"]),
        ]

    def __str__(self) -> str:
        return f"CalcBlock({self.block_key})"


class CalcModelAssembly(models.Model):
    """
    TECH+CORE: Связь \"модель -> блок\" с порядком исполнения (для MVP).

    Для будущего кеширования это критично:
      - блоки исполняются последовательно
      - outputs предыдущих блоков попадают во входы следующих

    Пример порядка:
      1) CAPEX
      2) Production
      3) UnitCosts
      4) PnL
      5) CashFlow
    """

    model = models.ForeignKey(
        CalcModel,
        on_delete=models.CASCADE,
        related_name="assemblies",
        help_text="Модель расчёта (для MVP: invest.pnl_cf.v1)."
    )
    block = models.ForeignKey(
        CalcBlock,
        on_delete=models.CASCADE,
        related_name="assemblies",
        help_text="Блок, входящий в модель (для MVP: CAPEX, Production, UnitCosts, PnL, CashFlow)."
    )
    order_no = models.PositiveIntegerField(
        help_text="Порядок исполнения блока (меньше — раньше; для MVP: 1, 2, 3, 4, 5)."
    )

    class Meta:
        db_table = "calc_model_assembly"
        unique_together = (("model", "block"),)
        indexes = [
            models.Index(fields=["model", "order_no"]),
        ]

    def __str__(self) -> str:
        return f"{self.model.model_key} -> {self.block.block_key} (#{self.order_no})"


class CalcBlockFormula(models.Model):
    """
    TECH+CORE: Явное перечисление формул, входящих в блок (для MVP).

    Это ключевая \"скоба\", без которой кеширование становится ненадёжным:
      - не нужно угадывать принадлежность формул по имени или по косвенным связям
      - можно батчем загрузить все формулы блока и построить структуру/кеш

    Важно:
      - formula_concept должен ссылаться на Concept (I.Formula через is_a),
        а выражение берётся из таблицы Formula (OneToOne к Concept) для вычислений.
    """

    block = models.ForeignKey(
        CalcBlock,
        on_delete=models.CASCADE,
        related_name="block_formulas",
        help_text="Блок, в который входит формула (для MVP: CAPEX, Production, UnitCosts, PnL, CashFlow)."
    )
    formula_concept = models.ForeignKey(
        Concept,
        on_delete=models.PROTECT,
        related_name="as_block_formula",
        help_text="Концепт формулы (обычно kind='I' и тип I.Formula через is_a) для вычислений."
    )

    class Meta:
        db_table = "calc_block_formula"
        unique_together = (("block", "formula_concept"),)
        indexes = [
            models.Index(fields=["block", "formula_concept"]),
        ]

    def __str__(self) -> str:
        return f"CalcBlockFormula({self.block.block_key} <- {self.formula_concept.key})"


# ======================================
# (ОПЦИОНАЛЬНО) АТРИБУТЫ РЕБРА КАК KV
# ======================================

class EdgeAttribute(models.Model):
    """
    NAVIS CORE (опционально): Атрибуты ребра как key-value.

    Зачем:
      - технические метаданные, которые не должны превращаться в отдельные типы связей:
        confidence, source_message_id, author_id, UI флаги и т.п.

    Важно:
      - не использовать для доменной семантики; доменная семантика живёт в I-концептах (как value_text).
    """

    edge = models.ForeignKey(
        Edge,
        on_delete=models.CASCADE,
        related_name="attrs",
        help_text="Ребро, к которому относится атрибут (для MVP: Edge(relation_type='describes'))."
    )
    key = models.CharField(
        max_length=100,
        help_text="Имя атрибута (для MVP: 'confidence', 'source_message_id')."
    )
    value_text = models.TextField(
        help_text="Значение атрибута в текстовом виде (для MVP: '0.95', '1234567890')."
    )

    class Meta:
        db_table = "navis_edge_attr"
        unique_together = (("edge", "key"),)
        indexes = [
            models.Index(fields=["key"]),
        ]

    def __str__(self) -> str:
        return f"EdgeAttribute({self.edge_id}, {self.key}={self.value_text[:30]})"