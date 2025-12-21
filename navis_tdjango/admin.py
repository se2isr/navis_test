from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Count
from django import forms
from .models import (
    Concept,
    ConceptLevel2,
    RelationType,
    Edge,
    Formula,
    InfoValue,
    CalcModel,
    CalcBlock,
    CalcModelAssembly,
    CalcBlockFormula,
    EdgeAttribute,
)


# ==================
# ФОРМЫ
# ==================

class ConceptLevel2Form(forms.ModelForm):
    """Форма для концептов второго уровня с автозаполнением kind"""
    
    class Meta:
        model = ConceptLevel2
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем kind readonly, но оставляем в форме
        self.fields['kind'].widget.attrs['readonly'] = False
        self.fields['kind'].help_text = ''  # Убираем help_text
        self.fields['kind'].label = 'Kind'  # Короткая метка
        # Делаем root_lv2 обязательным
        self.fields['root_lv2'].required = True
        self.fields['root_lv2'].empty_label = None  # Убираем пустую опцию "---------"
        self.fields['root_lv2'].help_text = ''  # Убираем help_text
        self.fields['root_lv2'].label = 'Родитель'  # Короткая метка
        # Убираем help_text у других полей
        self.fields['key'].help_text = ''
        self.fields['label'].help_text = ''
        self.fields['description'].help_text = ''
        self.fields['is_active'].help_text = ''


# ==================
# INLINE КЛАССЫ
# ==================

class EdgeAttributeInline(admin.TabularInline):
    """Инлайн для атрибутов ребра"""
    model = EdgeAttribute
    extra = 0
    fields = ('key', 'value_text')


class EdgeOutInline(admin.TabularInline):
    """Инлайн для исходящих связей концепта"""
    model = Edge
    fk_name = 'from_concept'
    extra = 0
    fields = ('relation_type', 'to_concept', 'weight', 'updated_at')
    readonly_fields = ('updated_at',)
    autocomplete_fields = ['to_concept', 'relation_type']
    verbose_name = "Исходящая связь"
    verbose_name_plural = "Исходящие связи"


class EdgeInInline(admin.TabularInline):
    """Инлайн для входящих связей концепта"""
    model = Edge
    fk_name = 'to_concept'
    extra = 0
    fields = ('from_concept', 'relation_type', 'weight', 'updated_at')
    readonly_fields = ('updated_at',)
    autocomplete_fields = ['from_concept', 'relation_type']
    verbose_name = "Входящая связь"
    verbose_name_plural = "Входящие связи"


class CalcModelAssemblyInline(admin.TabularInline):
    """Инлайн для сборки модели из блоков"""
    model = CalcModelAssembly
    extra = 0
    fields = ('block', 'order_no')
    autocomplete_fields = ['block']
    ordering = ('order_no',)


class CalcBlockFormulaInline(admin.TabularInline):
    """Инлайн для формул в блоке"""
    model = CalcBlockFormula
    extra = 0
    fields = ('formula_concept',)
    autocomplete_fields = ['formula_concept']


# ==================
# ADMIN КЛАССЫ
# ==================

# Базовый класс для концептов с общими методами
class BaseConceptAdmin(admin.ModelAdmin):
    list_display_links = ('label',)
    search_fields = ('key', 'label', 'description')
    readonly_fields = ('created_at', 'updated_at', 'edges_count', 'children_count')
    list_per_page = 50
    date_hierarchy = 'created_at'
    ordering = ['key']
    
    inlines = [EdgeOutInline, EdgeInInline]
    
    actions = ['activate_concepts', 'deactivate_concepts', 'export_to_csv']
    
    def key_colored(self, obj):
        """Ключ с цветовой подсветкой"""
        colors = {
            'O': '#2563eb',  # яркий голубой (материальные объекты)
            'P': '#ea580c',  # яркий оранжевый (процессы)
            'A': '#475569',  # темный серо-стальной (акторы)
            'I': '#16a34a',  # яркий зеленый (информация)
        }
        color = colors.get(obj.kind, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.key
        )
    key_colored.short_description = 'Ключ'
    key_colored.admin_order_field = 'key'
    
    def kind_badge(self, obj):
        """Красивый бейдж для типа концепта"""
        badges = {
            'O': ('<span style="background: #60a5fa; color: white; padding: 3px 8px; '
                  'border-radius: 3px;">Объект</span>'),
            'P': ('<span style="background: #f97316; color: white; padding: 3px 8px; '
                  'border-radius: 3px;">Процесс</span>'),
            'A': ('<span style="background: #64748b; color: white; padding: 3px 8px; '
                  'border-radius: 3px;">Актор</span>'),
            'I': ('<span style="background: #4ade80; color: white; padding: 3px 8px; '
                  'border-radius: 3px;">Информация</span>'),
        }
        return mark_safe(badges.get(obj.kind, obj.kind))
    kind_badge.short_description = 'Тип'
    kind_badge.admin_order_field = 'kind'
    
    def edges_count(self, obj):
        """Количество связей (входящих + исходящих)"""
        if obj.pk:
            out_count = obj.out_edges.count()
            in_count = obj.in_edges.count()
            return f"→ {out_count} | ← {in_count}"
        return "-"
    edges_count.short_description = 'Связи'
    
    def children_count(self, obj):
        """Количество дочерних концептов"""
        if obj.pk:
            return obj.children_lv2.count()
        return 0
    children_count.short_description = 'Дочерних'
    
    def activate_concepts(self, request, queryset):
        """Массовая активация концептов"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Активировано концептов: {updated}')
    activate_concepts.short_description = 'Активировать выбранные концепты'
    
    def deactivate_concepts(self, request, queryset):
        """Массовая деактивация концептов"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Деактивировано концептов: {updated}')
    deactivate_concepts.short_description = 'Деактивировать выбранные концепты'
    
    def export_to_csv(self, request, queryset):
        """Экспорт в CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="concepts.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Key', 'Label', 'Kind', 'Active', 'Root_LV2', 'Description'])
        
        for obj in queryset:
            root_key = obj.root_lv2.key if obj.root_lv2 else ''
            writer.writerow([obj.id, obj.key, obj.label, obj.kind, obj.is_active, root_key, obj.description])
        
        return response
    export_to_csv.short_description = 'Экспортировать в CSV'


# Админ для концептов первого уровня (корневые)
@admin.register(Concept)
class ConceptLevel1Admin(BaseConceptAdmin):
    list_display = ('id', 'key_colored', 'label', 'kind_badge', 'is_active', 'children_count', 'edges_count', 'updated_at')
    list_filter = ('kind', 'is_active', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('key', 'label', 'kind', 'is_active')
        }),
        ('Описание', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
        ('Техническая информация', {
            'fields': ('created_at', 'updated_at', 'children_count', 'edges_count'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Показываем только концепты первого уровня (root_lv2=NULL)"""
        qs = super().get_queryset(request)
        return qs.filter(root_lv2__isnull=True)
    
    def save_model(self, request, obj, form, change):
        """Гарантируем, что root_lv2 = NULL для концептов первого уровня"""
        obj.root_lv2 = None
        super().save_model(request, obj, form, change)
    
    class Meta:
        verbose_name = "Концепт (уровень 1)"
        verbose_name_plural = "Концепты (уровень 1)"


# Админ для концептов второго уровня и выше (с родителем)
@admin.register(ConceptLevel2)
class ConceptLevel2Admin(BaseConceptAdmin):
    form = ConceptLevel2Form
    list_display = ('id', 'key_colored', 'label', 'kind_badge', 'root_lv2_display', 'is_active', 'edges_count', 'updated_at')
    list_filter = ('kind', 'is_active', 'root_lv2', 'created_at', 'updated_at')
    # НЕ используем autocomplete_fields - он мешает нашим кнопкам
    
    fieldsets = (
        ('Основная информация', {
            'fields': (('root_lv2', 'kind'), ('key', 'label'), 'is_active'),
        }),
        ('Описание', {
            'fields': ('description',),
        }),
        ('Техническая информация', {
            'fields': (('created_at', 'updated_at'), 'edges_count'),
            'classes': ('collapse',)
        }),
    )
    
    class Media:
        css = {
            'all': ('admin/css/concept_level2_custom.css',)
        }
        js = ('admin/js/concept_level2_custom.js',)
    
    def root_lv2_display(self, obj):
        """Красивое отображение родителя с цветным бейджем"""
        if obj.root_lv2:
            colors = {
                'O': '#60a5fa',
                'P': '#f97316',
                'A': '#64748b',
                'I': '#4ade80',
            }
            color = colors.get(obj.root_lv2.kind, '#6c757d')
            return format_html(
                '<span style="background: {}; color: white; padding: 2px 6px; border-radius: 3px; margin-right: 5px;">{}</span> {}',
                color, obj.root_lv2.kind, obj.root_lv2.key
            )
        return '-'
    root_lv2_display.short_description = 'Родитель'
    root_lv2_display.admin_order_field = 'root_lv2'
    
    def get_queryset(self, request):
        """Показываем только концепты второго уровня и выше (root_lv2 != NULL)"""
        qs = super().get_queryset(request)
        return qs.filter(root_lv2__isnull=False)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Для root_lv2 показываем только концепты первого уровня с сортировкой"""
        if db_field.name == "root_lv2":
            kwargs["queryset"] = Concept.objects.filter(root_lv2__isnull=True).order_by('kind', 'key')
            # Добавляем кастомный виджет с фильтрацией
            kwargs["widget"] = forms.Select(attrs={
                'class': 'concept-select-with-filter',
                'data-filter-enabled': 'true'
            })
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def save_model(self, request, obj, form, change):
        """Автоматически копируем kind из родительского концепта"""
        if obj.root_lv2:
            obj.kind = obj.root_lv2.kind
        super().save_model(request, obj, form, change)
    
    def render_change_form(self, request, context, *args, **kwargs):
        """Добавляем данные о концептах для JavaScript"""
        # Получаем все концепты первого уровня с их kind
        concepts_data = list(
            Concept.objects.filter(root_lv2__isnull=True)
            .values('id', 'key', 'kind')
            .order_by('kind', 'key')
        )
        context['concepts_data'] = concepts_data
        return super().render_change_form(request, context, *args, **kwargs)
    
    class Meta:
        verbose_name = "Концепт (уровень 2+)"
        verbose_name_plural = "Концепты (уровень 2+)"


@admin.register(RelationType)
class RelationTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'key', 'alias_badge', 'label', 'parent', 'is_base', 'is_active', 'children_count')
    list_filter = ('is_base', 'is_active', 'parent')
    search_fields = ('key', 'alias', 'label', 'description')
    list_editable = ('is_base', 'is_active')
    readonly_fields = ('created_at', 'updated_at', 'children_count')
    list_per_page = 50
    ordering = ['key']
    autocomplete_fields = ['parent']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('key', 'alias', 'label', 'parent')
        }),
        ('Настройки', {
            'fields': ('is_base', 'is_active')
        }),
        ('Описание', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
        ('Техническая информация', {
            'fields': ('created_at', 'updated_at', 'children_count'),
            'classes': ('collapse',)
        }),
    )
    
    def alias_badge(self, obj):
        """Красивый бейдж для алиаса"""
        if obj.alias:
            return format_html(
                '<code style="background: #f4f4f4; padding: 2px 6px; border-radius: 3px;">{}</code>',
                obj.alias
            )
        return '-'
    alias_badge.short_description = 'Алиас'
    alias_badge.admin_order_field = 'alias'
    
    def children_count(self, obj):
        """Количество дочерних типов связей"""
        if obj.pk:
            return obj.children.count()
        return 0
    children_count.short_description = 'Дочерних типов'


@admin.register(Edge)
class EdgeAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_concept_display', 'relation_display', 'to_concept_display', 'weight', 'attrs_count', 'updated_at')
    list_filter = ('relation_type', 'created_at', 'updated_at')
    search_fields = ('from_concept__key', 'to_concept__key', 'relation_type__key')
    readonly_fields = ('created_at', 'updated_at', 'attrs_count')
    autocomplete_fields = ['from_concept', 'to_concept', 'relation_type']
    list_per_page = 50
    ordering = ['from_concept__key', 'relation_type__key', 'to_concept__key']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Связь', {
            'fields': ('from_concept', 'relation_type', 'to_concept', 'weight')
        }),
        ('Техническая информация', {
            'fields': ('created_at', 'updated_at', 'attrs_count'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [EdgeAttributeInline]
    
    def from_concept_display(self, obj):
        """Красивое отображение исходного концепта"""
        return format_html(
            '<a href="/admin/navis_tdjango/concept/{}/change/">{}</a>',
            obj.from_concept.id, obj.from_concept.key
        )
    from_concept_display.short_description = 'От'
    from_concept_display.admin_order_field = 'from_concept'
    
    def to_concept_display(self, obj):
        """Красивое отображение целевого концепта"""
        return format_html(
            '<a href="/admin/navis_tdjango/concept/{}/change/">{}</a>',
            obj.to_concept.id, obj.to_concept.key
        )
    to_concept_display.short_description = 'К'
    to_concept_display.admin_order_field = 'to_concept'
    
    def relation_display(self, obj):
        """Красивое отображение типа связи"""
        alias = obj.relation_type.alias or ''
        return format_html(
            '<span style="color: #007bff; font-weight: bold;">{} {}</span>',
            obj.relation_type.key, f'({alias})' if alias else ''
        )
    relation_display.short_description = 'Тип связи'
    relation_display.admin_order_field = 'relation_type'
    
    def attrs_count(self, obj):
        """Количество атрибутов ребра"""
        if obj.pk:
            return obj.attrs.count()
        return 0
    attrs_count.short_description = 'Атрибутов'


@admin.register(Formula)
class FormulaAdmin(admin.ModelAdmin):
    list_display = ('concept_key', 'language', 'expression_preview', 'updated_at')
    list_filter = ('language', 'updated_at')
    search_fields = ('concept__key', 'expression')
    readonly_fields = ('updated_at', 'concept_info')
    autocomplete_fields = ['concept']
    list_per_page = 50
    ordering = ['concept__key']
    
    fieldsets = (
        ('Связь с концептом', {
            'fields': ('concept', 'concept_info')
        }),
        ('Формула', {
            'fields': ('language', 'expression')
        }),
        ('Техническая информация', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )
    
    def concept_key(self, obj):
        """Ключ концепта"""
        return obj.concept.key
    concept_key.short_description = 'Концепт'
    concept_key.admin_order_field = 'concept__key'
    
    def expression_preview(self, obj):
        """Превью выражения (первые 100 символов)"""
        if len(obj.expression) > 100:
            return format_html(
                '<code style="background: #f4f4f4; padding: 2px 6px;">{}</code>',
                obj.expression[:100] + '...'
            )
        return format_html(
            '<code style="background: #f4f4f4; padding: 2px 6px;">{}</code>',
            obj.expression
        )
    expression_preview.short_description = 'Выражение'
    
    def concept_info(self, obj):
        """Информация о концепте"""
        if obj.concept:
            return format_html(
                'ID: {} | Key: {} | Kind: {} | <a href="/admin/navis_tdjango/concept/{}/change/">Открыть</a>',
                obj.concept.id, obj.concept.key, obj.concept.get_kind_display(), obj.concept.id
            )
        return '-'
    concept_info.short_description = 'Информация о концепте'


@admin.register(InfoValue)
class InfoValueAdmin(admin.ModelAdmin):
    list_display = ('concept_key', 'value_display', 'unit', 'updated_at')
    list_filter = ('unit', 'updated_at')
    search_fields = ('concept__key', 'value_text', 'unit')
    readonly_fields = ('updated_at', 'concept_info')
    autocomplete_fields = ['concept']
    list_per_page = 50
    ordering = ['concept__key']
    
    fieldsets = (
        ('Связь с концептом', {
            'fields': ('concept', 'concept_info')
        }),
        ('Значение', {
            'fields': ('value_num', 'value_text', 'unit')
        }),
        ('Техническая информация', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )
    
    def concept_key(self, obj):
        """Ключ концепта"""
        return obj.concept.key
    concept_key.short_description = 'Концепт'
    concept_key.admin_order_field = 'concept__key'
    
    def value_display(self, obj):
        """Красивое отображение значения"""
        if obj.value_num is not None:
            return format_html(
                '<strong style="color: #28a745;">{}</strong>',
                obj.value_num
            )
        elif obj.value_text:
            return format_html(
                '<span style="color: #007bff;">{}</span>',
                obj.value_text[:50] + ('...' if len(obj.value_text) > 50 else '')
            )
        return '-'
    value_display.short_description = 'Значение'
    
    def concept_info(self, obj):
        """Информация о концепте"""
        if obj.concept:
            return format_html(
                'ID: {} | Key: {} | Kind: {} | <a href="/admin/navis_tdjango/concept/{}/change/">Открыть</a>',
                obj.concept.id, obj.concept.key, obj.concept.get_kind_display(), obj.concept.id
            )
        return '-'
    concept_info.short_description = 'Информация о концепте'


@admin.register(CalcModel)
class CalcModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'model_key', 'blocks_count', 'created_at')
    search_fields = ('model_key', 'description')
    readonly_fields = ('created_at', 'blocks_count')
    list_per_page = 50
    ordering = ['model_key']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('model_key', 'description')
        }),
        ('Техническая информация', {
            'fields': ('created_at', 'blocks_count'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [CalcModelAssemblyInline]
    
    def blocks_count(self, obj):
        """Количество блоков в модели"""
        if obj.pk:
            return obj.assemblies.count()
        return 0
    blocks_count.short_description = 'Блоков'


@admin.register(CalcBlock)
class CalcBlockAdmin(admin.ModelAdmin):
    list_display = ('id', 'block_key', 'formulas_count', 'models_count')
    search_fields = ('block_key', 'description')
    readonly_fields = ('formulas_count', 'models_count')
    list_per_page = 50
    ordering = ['block_key']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('block_key', 'description')
        }),
        ('Статистика', {
            'fields': ('formulas_count', 'models_count'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [CalcBlockFormulaInline]
    
    def formulas_count(self, obj):
        """Количество формул в блоке"""
        if obj.pk:
            return obj.block_formulas.count()
        return 0
    formulas_count.short_description = 'Формул'
    
    def models_count(self, obj):
        """В скольких моделях используется блок"""
        if obj.pk:
            return obj.assemblies.count()
        return 0
    models_count.short_description = 'В моделях'


@admin.register(CalcModelAssembly)
class CalcModelAssemblyAdmin(admin.ModelAdmin):
    list_display = ('id', 'model', 'block', 'order_no')
    list_filter = ('model', 'block')
    search_fields = ('model__model_key', 'block__block_key')
    list_editable = ('order_no',)
    autocomplete_fields = ['model', 'block']
    ordering = ('model', 'order_no')
    list_per_page = 50
    
    fieldsets = (
        ('Сборка модели', {
            'fields': ('model', 'block', 'order_no')
        }),
    )


@admin.register(CalcBlockFormula)
class CalcBlockFormulaAdmin(admin.ModelAdmin):
    list_display = ('id', 'block', 'formula_concept_key')
    list_filter = ('block',)
    search_fields = ('block__block_key', 'formula_concept__key')
    autocomplete_fields = ['block', 'formula_concept']
    list_per_page = 50
    ordering = ['block__block_key', 'formula_concept__key']
    
    fieldsets = (
        ('Формула в блоке', {
            'fields': ('block', 'formula_concept')
        }),
    )
    
    def formula_concept_key(self, obj):
        """Ключ концепта формулы"""
        return obj.formula_concept.key
    formula_concept_key.short_description = 'Формула'
    formula_concept_key.admin_order_field = 'formula_concept__key'


@admin.register(EdgeAttribute)
class EdgeAttributeAdmin(admin.ModelAdmin):
    list_display = ('id', 'edge_display', 'key', 'value_preview')
    list_filter = ('key',)
    search_fields = ('edge__from_concept__key', 'edge__to_concept__key', 'key', 'value_text')
    autocomplete_fields = ['edge']
    list_per_page = 50
    ordering = ['key']
    
    fieldsets = (
        ('Атрибут ребра', {
            'fields': ('edge', 'key', 'value_text')
        }),
    )
    
    def edge_display(self, obj):
        """Красивое отображение ребра"""
        return format_html(
            '<a href="/admin/navis_tdjango/edge/{}/change/">{} → {}</a>',
            obj.edge.id,
            obj.edge.from_concept.key[:30],
            obj.edge.to_concept.key[:30]
        )
    edge_display.short_description = 'Ребро'
    edge_display.admin_order_field = 'edge'
    
    def value_preview(self, obj):
        """Превью значения (первые 50 символов)"""
        if len(obj.value_text) > 50:
            return obj.value_text[:50] + '...'
        return obj.value_text
    value_preview.short_description = 'Значение'


# Настройка заголовков админки
admin.site.site_header = "NAVIS Admin"
admin.site.site_title = "NAVIS"
admin.site.index_title = "Управление NAVIS"
