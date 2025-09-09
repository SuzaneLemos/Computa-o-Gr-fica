import pygame
import numpy as np
import math
from enum import Enum
import colorsys

class DrawMode(Enum):
    """Modos de desenho disponíveis no programa"""
    SELECT = 0    # Modo seleção
    POINT = 1     # Desenhar pontos
    LINE = 2      # Desenhar linhas
    CIRCLE = 3    # Desenhar círculos
    POLYGON = 4   # Desenhar polígonos
    FREEHAND = 5  # Desenho livre

class TransformMode(Enum):
    """Tipos de transformações geométricas 2D"""
    TRANSLATE = 0   # Translação
    ROTATE = 1      # Rotação
    SCALE = 2       # Escala
    REFLECT_X = 3   # Reflexão no eixo X
    REFLECT_Y = 4   # Reflexão no eixo Y
    REFLECT_XY = 5  # Reflexão nos eixos X e Y

class Shape:
    """Classe para representar formas geométricas"""
    def __init__(self, shape_type, points, color=(0, 0, 0), thickness=2):
        self.type = shape_type          # Tipo da forma
        self.points = points            # Lista de pontos da forma
        self.color = color              # Cor da forma
        self.thickness = thickness      # Espessura da forma
        self.selected = False           # Se a forma está selecionada
        self.original_points = points.copy()  # Backup dos pontos originais

class ColorWheel:
    """Classe para criar e gerenciar roda cromática"""
    def __init__(self, center, radius):
        self.center = center
        self.radius = radius
        self.inner_radius = radius * 0.3  # Raio interno para saturação
        self.wheel_surface = None
        self.create_wheel()
    
    def create_wheel(self):
        """Cria a superfície da roda cromática"""
        size = self.radius * 2
        self.wheel_surface = pygame.Surface((size, size), pygame.SRCALPHA)
        
        # Cria a roda cromática pixel por pixel
        for x in range(size):
            for y in range(size):
                # Calcula distância do centro
                dx = x - self.radius
                dy = y - self.radius
                distance = math.sqrt(dx * dx + dy * dy)
                
                if self.inner_radius <= distance <= self.radius:
                    # Calcula ângulo (hue)
                    angle = math.atan2(dy, dx)
                    hue = (angle + math.pi) / (2 * math.pi)  # 0 a 1
                    
                    # Calcula saturação baseada na distância
                    saturation = (distance - self.inner_radius) / (self.radius - self.inner_radius)
                    
                    # Converte HSV para RGB
                    rgb = colorsys.hsv_to_rgb(hue, saturation, 1.0)
                    color = (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))
                    
                    self.wheel_surface.set_at((x, y), color)
    
    def get_color_at_pos(self, pos):
        """Retorna a cor na posição clicada"""
        dx = pos[0] - self.center[0]
        dy = pos[1] - self.center[1]
        distance = math.sqrt(dx * dx + dy * dy)
        
        if self.inner_radius <= distance <= self.radius:
            # Calcula hue e saturação
            angle = math.atan2(dy, dx)
            hue = (angle + math.pi) / (2 * math.pi)
            saturation = (distance - self.inner_radius) / (self.radius - self.inner_radius)
            
            # Converte para RGB
            rgb = colorsys.hsv_to_rgb(hue, saturation, 1.0)
            return (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))
        
        return None
    
    def draw(self, screen):
        """Desenha a roda cromática"""
        if self.wheel_surface:
            wheel_rect = self.wheel_surface.get_rect(center=self.center)
            screen.blit(self.wheel_surface, wheel_rect)
            
            # Desenha borda
            pygame.draw.circle(screen, (100, 100, 100), self.center, self.radius, 2)
            pygame.draw.circle(screen, (100, 100, 100), self.center, self.inner_radius, 2)

class PaintCG:
    """Classe principal do programa Paint - Computação Gráfica"""
    
    def __init__(self):
        """Inicializa o programa e configura a interface"""
        pygame.init()
        
        # Configurações da janela
        self.width = 1300
        self.height = 900
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Paint Pro - Computação Gráfica")
        
        # Paleta de cores moderna
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.BLUE = (52, 152, 219)
        self.DARK_BLUE = (41, 128, 185)
        self.RED = (231, 76, 60)
        self.GREEN = (46, 204, 113)
        self.ORANGE = (230, 126, 34)
        self.PURPLE = (155, 89, 182)
        self.GRAY = (149, 165, 166)
        self.LIGHT_GRAY = (236, 240, 241)
        self.DARK_GRAY = (52, 73, 94)
        self.ACCENT = (26, 188, 156)
        
        # Estado do programa
        self.shapes = []                # Lista de formas desenhadas
        self.current_polygon = []       # Polígono em construção
        self.current_freehand = []      # Desenho livre em construção
        self.drawing_freehand = False   # Se está desenhando à mão livre
        self.draw_mode = DrawMode.SELECT
        self.transform_mode = TransformMode.TRANSLATE
        self.selecting = False          # Se está fazendo seleção
        self.selection_start = None     # Início da seleção
        self.selection_rect = None      # Retângulo de seleção
        
        # Configurações da interface (painel mais largo)
        self.font_title = pygame.font.Font(None, 28)
        self.font_button = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 18)
        self.panel_width = 320          # Painel ainda mais largo
        self.draw_area = pygame.Rect(self.panel_width, 0, self.width - self.panel_width, self.height)
        
        # Variáveis de transformação (escala melhorada)
        self.transform_factor = 1.0  # Agora pode ser < 1.0 para diminuir
        self.rotation_angle = 0.0
        self.rotating = False
        self.rotation_start_pos = None
        
        # Controle de rotação por input
        self.rotation_input_active = False
        self.rotation_input_text = ""
        
        # Controle de espessura
        self.brush_thickness = 2
        self.thickness_input_active = False
        self.thickness_input_text = ""
        
        # Sistema de zoom
        self.zoom_factor = 1.0
        self.zoom_offset = [0, 0]  # Offset para pan quando com zoom
        self.min_zoom = 0.1
        self.max_zoom = 5.0
        
        # Roda cromática
        self.color_wheel = ColorWheel((150, 300), 80)
        self.current_draw_color = self.BLACK
        
        # Configurações para fluidez
        self.clock = pygame.time.Clock()
        self.fps = 120                  # FPS alto para fluidez
        self.fullscreen = False
        
        # Áreas de botões (corrigidas)
        self.button_areas = []
        self.transform_button_areas = []
        
    def create_button_areas(self):
        """Cria as áreas clicáveis dos botões (corrige problema de clique)"""
        self.button_areas = []
        self.transform_button_areas = []
        
        # Botões de desenho
        y_start = 280
        for i in range(6):  # Agora temos 6 modos (incluindo freehand)
            rect = pygame.Rect(15, y_start + i * 30, 290, 26)
            self.button_areas.append(rect)
        
        # Botões de transformação
        y_start = 490
        for i in range(6):
            rect = pygame.Rect(15, y_start + i * 28, 290, 25)
            self.transform_button_areas.append(rect)
    
    def draw_interface(self):
        """Desenha toda a interface do programa"""
        # Recria áreas dos botões
        self.create_button_areas()
        
        # Painel lateral com gradiente sutil
        panel_rect = pygame.Rect(0, 0, self.panel_width, self.height)
        pygame.draw.rect(self.screen, self.LIGHT_GRAY, panel_rect)
        
        # Linha separadora elegante com efeito 3D
        pygame.draw.line(self.screen, (200, 200, 200), 
                        (self.panel_width - 4, 0), (self.panel_width - 4, self.height), 2)
        pygame.draw.line(self.screen, self.DARK_GRAY, 
                        (self.panel_width - 2, 0), (self.panel_width - 2, self.height), 2)
        
        # Título principal com estilo
        title = self.font_title.render("Paint PRO", True, self.DARK_BLUE)
        self.screen.blit(title, (20, 15))
        
        # Linha decorativa abaixo do título
        pygame.draw.line(self.screen, self.DARK_BLUE, (20, 45), (self.panel_width - 30, 45), 2)
        
        # Seção de ferramentas de desenho
        y_offset = 270
        section_title = self.font_button.render("Ferramentas:", True, self.DARK_GRAY)
        self.screen.blit(section_title, (20, y_offset - 5))
        
        # Botões de desenho 
        buttons = [
            ("Selecionar", DrawMode.SELECT, self.ACCENT),
            ("Ponto", DrawMode.POINT, self.BLUE),
            ("Linha", DrawMode.LINE, self.GREEN),
            ("Círculo", DrawMode.CIRCLE, self.RED),
            ("Polígono", DrawMode.POLYGON, self.PURPLE),
            ("Desenho Livre", DrawMode.FREEHAND, self.ORANGE)
        ]
        
        for i, (text, mode, color) in enumerate(buttons):
            is_active = self.draw_mode == mode
            button_rect = self.button_areas[i]
            
            # Efeito de sombra
            if is_active:
                shadow_rect = pygame.Rect(button_rect.x + 3, button_rect.y + 3, 
                                        button_rect.width, button_rect.height)
                pygame.draw.rect(self.screen, (180, 180, 180), shadow_rect, border_radius=10)
            
            # Cor do botão
            btn_color = color if is_active else self.WHITE
            pygame.draw.rect(self.screen, btn_color, button_rect, border_radius=10)
            
            # Borda com espessura variável
            border_width = 3 if is_active else 2
            pygame.draw.rect(self.screen, color, button_rect, border_width, border_radius=10)
            
            # Texto do botão
            text_color = self.WHITE if is_active else color
            text_surf = self.font_button.render(text, True, text_color)
            text_rect = text_surf.get_rect(center=button_rect.center)
            self.screen.blit(text_surf, text_rect)
        
        # Roda cromática
        y_offset = 60
        color_title = self.font_button.render("Cor:", True, self.DARK_GRAY)
        self.screen.blit(color_title, (15, y_offset))

        # Desenha roda cromática
        self.color_wheel.center = (140, y_offset + 80)  # Mover para cima
        self.color_wheel.draw(self.screen)

        # Mostra cor atual
        color_preview = pygame.Rect(250, y_offset + 60, 40, 40)
        pygame.draw.rect(self.screen, self.current_draw_color, color_preview, border_radius=8)
        pygame.draw.rect(self.screen, self.DARK_GRAY, color_preview, 3, border_radius=8)
        
        # Controle de espessura
        thickness_title = self.font_button.render("Espessura:", True, self.DARK_GRAY)
        self.screen.blit(thickness_title, (20, 230))
        
        # Campo de input de espessura
        thickness_input_rect = pygame.Rect(150, 235, 80, 25)
        input_color = self.ACCENT if self.thickness_input_active else self.WHITE
        pygame.draw.rect(self.screen, input_color, thickness_input_rect, border_radius=5)
        pygame.draw.rect(self.screen, self.DARK_GRAY, thickness_input_rect, 2, border_radius=5)
        
        # Texto do input de espessura
        display_text = self.thickness_input_text if self.thickness_input_active else str(self.brush_thickness)
        thickness_text = self.font_small.render(display_text, True, self.BLACK)
        self.screen.blit(thickness_text, (thickness_input_rect.x + 5, thickness_input_rect.y + 5))
        
        # Cursor piscando para espessura
        if self.thickness_input_active and pygame.time.get_ticks() % 1000 < 500:
            cursor_x = thickness_input_rect.x + 5 + thickness_text.get_width()
            pygame.draw.line(self.screen, self.BLACK, 
                           (cursor_x, thickness_input_rect.y + 3), 
                           (cursor_x, thickness_input_rect.y + 22), 2)
        
        # Botões +/- para espessura
        thickness_inc_rect = pygame.Rect(125, 235, 20, 12)
        thickness_dec_rect = pygame.Rect(125, 248, 20, 12)
        
        pygame.draw.rect(self.screen, self.GREEN, thickness_inc_rect, border_radius=3)
        pygame.draw.rect(self.screen, self.RED, thickness_dec_rect, border_radius=3)
        
        # Símbolos + e -
        plus_text = pygame.font.Font(None, 16).render("+", True, self.WHITE)
        minus_text = pygame.font.Font(None, 16).render("-", True, self.WHITE)
        self.screen.blit(plus_text, (thickness_inc_rect.centerx - 4, thickness_inc_rect.centery - 6))
        self.screen.blit(minus_text, (thickness_dec_rect.centerx - 4, thickness_dec_rect.centery - 6))
        
        # Preview da espessura
        preview_center = (280, 250)
        pygame.draw.circle(self.screen, self.current_draw_color, preview_center, 
                         max(1, min(15, self.brush_thickness)))
        pygame.draw.circle(self.screen, self.DARK_GRAY, preview_center, 
                         max(3, min(17, self.brush_thickness + 2)), 2)
        
        # Seção de transformações
        y_offset = 475
        section_title = self.font_button.render("Transformações:", True, self.DARK_GRAY)
        self.screen.blit(section_title, (20, y_offset - 5))
        
        transforms = [
            ("Translação", TransformMode.TRANSLATE, self.BLUE),
            ("Rotação", TransformMode.ROTATE, self.GREEN),
            ("Escala", TransformMode.SCALE, self.ORANGE),
            ("Reflexão X", TransformMode.REFLECT_X, self.RED),
            ("Reflexão Y", TransformMode.REFLECT_Y, self.PURPLE),
            ("Reflexão XY", TransformMode.REFLECT_XY, self.ACCENT)
        ]
        
        for i, (text, mode, color) in enumerate(transforms):
            is_active = self.transform_mode == mode
            button_rect = self.transform_button_areas[i]
            
            # Cor do botão
            btn_color = color if is_active else self.WHITE
            pygame.draw.rect(self.screen, btn_color, button_rect, border_radius=8)
            pygame.draw.rect(self.screen, color, button_rect, 2 if not is_active else 3, border_radius=8)
            
            # Texto do botão
            text_color = self.WHITE if is_active else color
            text_surf = self.font_small.render(text, True, text_color)
            text_rect = text_surf.get_rect(center=button_rect.center)
            self.screen.blit(text_surf, text_rect)
        
        # Painel de controle de valores
        y_offset = 670
        control_bg = pygame.Rect(15, y_offset, 290, 140)
        pygame.draw.rect(self.screen, self.WHITE, control_bg, border_radius=12)
        pygame.draw.rect(self.screen, self.DARK_BLUE, control_bg, 3, border_radius=12)
        
        # Título do painel de controle
        control_title = self.font_button.render("🎛 Controles:", True, self.DARK_BLUE)
        self.screen.blit(control_title, (25, y_offset + 10))
        
        # Controles específicos por tipo de transformação
        if self.transform_mode == TransformMode.ROTATE:
            # Campo de input para ângulo
            angle_label = self.font_small.render("Ângulo (graus):", True, self.DARK_GRAY)
            self.screen.blit(angle_label, (25, y_offset + 35))
            
            # Caixa de input
            input_rect = pygame.Rect(25, y_offset + 55, 200, 25)
            input_color = self.ACCENT if self.rotation_input_active else self.LIGHT_GRAY
            pygame.draw.rect(self.screen, input_color, input_rect, border_radius=5)
            pygame.draw.rect(self.screen, self.DARK_GRAY, input_rect, 2, border_radius=5)
            
            # Texto do input
            display_text = self.rotation_input_text if self.rotation_input_active else str(int(self.rotation_angle))
            input_text = self.font_small.render(display_text, True, self.BLACK)
            self.screen.blit(input_text, (input_rect.x + 5, input_rect.y + 5))
            
            # Cursor piscando
            if self.rotation_input_active and pygame.time.get_ticks() % 1000 < 500:
                cursor_x = input_rect.x + 5 + input_text.get_width()
                pygame.draw.line(self.screen, self.BLACK, 
                               (cursor_x, input_rect.y + 3), (cursor_x, input_rect.y + 22), 2)
            
            # Botões de incremento/decremento
            inc_rect = pygame.Rect(235, y_offset + 55, 20, 12)
            dec_rect = pygame.Rect(235, y_offset + 68, 20, 12)
            
            pygame.draw.rect(self.screen, self.GREEN, inc_rect, border_radius=3)
            pygame.draw.rect(self.screen, self.RED, dec_rect, border_radius=3)
            
            # Símbolos + e -
            plus_text = pygame.font.Font(None, 16).render("+", True, self.WHITE)
            minus_text = pygame.font.Font(None, 16).render("-", True, self.WHITE)
            self.screen.blit(plus_text, (inc_rect.centerx - 4, inc_rect.centery - 6))
            self.screen.blit(minus_text, (dec_rect.centerx - 4, dec_rect.centery - 6))
            
            # Instruções para rotação
            if self.rotating:
                rotate_info = "🔄 Arrastando..."
                rotate_surf = self.font_small.render(rotate_info, True, self.GREEN)
                self.screen.blit(rotate_surf, (25, y_offset + 90))
            else:
                info1 = "• Clique no campo para editar"
                info2 = "• Use +/- para ajustar"
                info3 = "• Arraste objetos para rotacionar"
                
                self.screen.blit(self.font_small.render(info1, True, self.DARK_GRAY), (25, y_offset + 90))
                self.screen.blit(pygame.font.Font(None, 16).render(info2, True, self.DARK_GRAY), (25, y_offset + 105))
                self.screen.blit(pygame.font.Font(None, 16).render(info3, True, self.DARK_GRAY), (25, y_offset + 120))
        else:
            # Controles para outras transformações
            factor_label = self.font_small.render(f"Fator: {self.transform_factor:.2f}", True, self.DARK_GRAY)
            self.screen.blit(factor_label, (25, y_offset + 35))
            
            # Barra de progresso visual para o fator (ajustada para valores menores)
            progress_bg = pygame.Rect(25, y_offset + 55, 200, 12)
            pygame.draw.rect(self.screen, self.LIGHT_GRAY, progress_bg, border_radius=6)
            
            # Calcula progresso (fator de 0.1 a 3.0)
            progress = (self.transform_factor - 0.1) / 2.9
            progress_width = int(progress * 200)
            progress_rect = pygame.Rect(25, y_offset + 55, max(4, progress_width), 12)
            
            # Cor da barra baseada no valor
            if self.transform_factor < 1.0:
                bar_color = self.RED  # Diminuindo
            elif self.transform_factor > 1.0:
                bar_color = self.GREEN  # Aumentando
            else:
                bar_color = self.BLUE  # Normal
            
            pygame.draw.rect(self.screen, bar_color, progress_rect, border_radius=6)
            
            # Linha de referência em 1.0 (valor neutro)
            neutral_pos = int((1.0 - 0.1) / 2.9 * 200) + 25
            pygame.draw.line(self.screen, self.DARK_GRAY, 
                           (neutral_pos, y_offset + 53), (neutral_pos, y_offset + 69), 2)
            
            # Botões de ajuste fino
            dec_button = pygame.Rect(235, y_offset + 55, 25, 12)
            inc_button = pygame.Rect(265, y_offset + 55, 25, 12)
            
            pygame.draw.rect(self.screen, self.RED, dec_button, border_radius=3)
            pygame.draw.rect(self.screen, self.GREEN, inc_button, border_radius=3)
            
            dec_text = pygame.font.Font(None, 14).render("−", True, self.WHITE)
            inc_text = pygame.font.Font(None, 14).render("+", True, self.WHITE)
            self.screen.blit(dec_text, (dec_button.centerx - 3, dec_button.centery - 5))
            self.screen.blit(inc_text, (inc_button.centerx - 3, inc_button.centery - 5))
            
            # Instruções
            info_lines = [
                "• Scroll: ajustar fator",
                "• +/-: ajuste fino",
                "• < 1.0: diminuir, > 1.0: aumentar"
            ]
            
            for i, info in enumerate(info_lines):
                info_surf = pygame.font.Font(None, 15).render(info, True, self.DARK_GRAY)
                self.screen.blit(info_surf, (25, y_offset + 75 + i * 15))
        
        # Controles de Zoom (nova seção)
        zoom_title = self.font_button.render("🔍 Zoom da Tela:", True, self.DARK_GRAY)
        self.screen.blit(zoom_title, (20, y_offset + 150))
        
        # Botões de zoom
        zoom_out_btn = pygame.Rect(20, y_offset + 175, 60, 25)
        zoom_reset_btn = pygame.Rect(90, y_offset + 175, 60, 25)
        zoom_in_btn = pygame.Rect(160, y_offset + 175, 60, 25)
        
        pygame.draw.rect(self.screen, self.RED, zoom_out_btn, border_radius=5)
        pygame.draw.rect(self.screen, self.BLUE, zoom_reset_btn, border_radius=5)
        pygame.draw.rect(self.screen, self.GREEN, zoom_in_btn, border_radius=5)
        
        zoom_out_text = self.font_small.render("−", True, self.WHITE)
        zoom_reset_text = pygame.font.Font(None, 16).render("1:1", True, self.WHITE)
        zoom_in_text = self.font_small.render("+", True, self.WHITE)
        
        self.screen.blit(zoom_out_text, (zoom_out_btn.centerx - 4, zoom_out_btn.centery - 8))
        self.screen.blit(zoom_reset_text, (zoom_reset_btn.centerx - 8, zoom_reset_btn.centery - 8))
        self.screen.blit(zoom_in_text, (zoom_in_btn.centerx - 4, zoom_in_btn.centery - 8))
        
        # Mostra nível de zoom atual
        zoom_level_text = f"Zoom: {self.zoom_factor:.1f}x"
        zoom_surf = pygame.font.Font(None, 16).render(zoom_level_text, True, self.DARK_GRAY)
        self.screen.blit(zoom_surf, (230, y_offset + 182))
        
        # Botões superiores
        fullscreen_btn = pygame.Rect(self.width - 60, 10, 40, 25)
        help_btn = pygame.Rect(self.width - 110, 10, 25, 25)
        pygame.draw.rect(self.screen, self.BLUE, fullscreen_btn, border_radius=5)
        pygame.draw.rect(self.screen, self.GREEN, help_btn, border_radius=12)
        fs_text = self.font_small.render("⛶", True, self.WHITE)
        help_text = self.font_button.render("?", True, self.WHITE)
        self.screen.blit(fs_text, (fullscreen_btn.centerx - 6, fullscreen_btn.centery - 8))
        self.screen.blit(help_text, (help_btn.centerx - 6, help_btn.centery - 8))
        
        # Instruções gerais na parte inferior
        y_offset = 880
        general_info = [
            "Atalhos: C (limpar) • Esc (finalizar)"
        ]
        
        for i, text in enumerate(general_info):
            text_surf = pygame.font.Font(None, 15).render(text, True, self.DARK_BLUE)
            self.screen.blit(text_surf, (20, y_offset + i * 18))
    
    def handle_panel_click(self, pos):
        """Gerencia cliques no painel lateral (corrigido)"""
        x, y = pos
        if x > self.panel_width:
            # Botões superiores
            fullscreen_btn = pygame.Rect(self.width - 60, 10, 40, 25)
            help_btn = pygame.Rect(self.width - 110, 10, 25, 25)
            if fullscreen_btn.collidepoint(pos):
                self.fullscreen = not self.fullscreen
                if self.fullscreen:
                    self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                else:
                    self.screen = pygame.display.set_mode((self.width, self.height))
                return True
            if help_btn.collidepoint(pos):
                print("AJUDA: Use setas para translação, clique em formas para selecionar, ESC finaliza polígono")
                return True
            return False
            
        # Botões de desenho (usando áreas corrigidas)
        for i, rect in enumerate(self.button_areas):
            if rect.collidepoint(pos):
                self.draw_mode = list(DrawMode)[i]
                if self.draw_mode != DrawMode.POLYGON:
                    self.current_polygon = []
                if self.draw_mode != DrawMode.FREEHAND:
                    self.current_freehand = []
                    self.drawing_freehand = False
                return True
        
        # Roda cromática
        color = self.color_wheel.get_color_at_pos(pos)
        if color:
            self.current_draw_color = color
            return True
        
        # Campo de input de espessura
        thickness_input_rect = pygame.Rect(150, 235, 80, 25)
        if thickness_input_rect.collidepoint(pos):
            self.thickness_input_active = True
            self.thickness_input_text = ""
            return True
        
        # Botões +/- de espessura
        thickness_inc_rect = pygame.Rect(125, 235, 20, 12)
        thickness_dec_rect = pygame.Rect(125, 248, 20, 12)
        
        if thickness_inc_rect.collidepoint(pos):
            self.brush_thickness = min(50, self.brush_thickness + 1)
            return True
        elif thickness_dec_rect.collidepoint(pos):
            self.brush_thickness = max(1, self.brush_thickness - 1)
            return True
        
        # Botões de transformação (usando áreas corrigidas)
        for i, rect in enumerate(self.transform_button_areas):
            if rect.collidepoint(pos):
                self.transform_mode = list(TransformMode)[i]
                self.rotation_input_active = False
                return True
        
        # Controles de transformação
        y_offset = 600
        
        # Controles de rotação
        if self.transform_mode == TransformMode.ROTATE:
            # Campo de input de ângulo
            input_rect = pygame.Rect(25, y_offset + 55, 200, 25)
            if input_rect.collidepoint(pos):
                self.rotation_input_active = True
                self.rotation_input_text = ""
                return True
            
            # Botões de incremento/decremento rotação
            inc_rect = pygame.Rect(235, y_offset + 55, 20, 12)
            dec_rect = pygame.Rect(235, y_offset + 68, 20, 12)
            
            if inc_rect.collidepoint(pos):
                self.rotation_angle = (self.rotation_angle + 5) % 360
                return True
            elif dec_rect.collidepoint(pos):
                self.rotation_angle = (self.rotation_angle - 5) % 360
                return True
        else:
            # Botões de ajuste de fator de transformação
            dec_button = pygame.Rect(235, y_offset + 55, 25, 12)
            inc_button = pygame.Rect(265, y_offset + 55, 25, 12)
            
            if dec_button.collidepoint(pos):
                self.transform_factor = max(0.1, self.transform_factor - 0.1)
                return True
            elif inc_button.collidepoint(pos):
                self.transform_factor = min(3.0, self.transform_factor + 0.1)
                return True
        
        # Controles de Zoom
        zoom_out_btn = pygame.Rect(20, y_offset + 175, 60, 25)
        zoom_reset_btn = pygame.Rect(90, y_offset + 175, 60, 25)
        zoom_in_btn = pygame.Rect(160, y_offset + 175, 60, 25)
        
        if zoom_out_btn.collidepoint(pos):
            self.zoom_out()
            return True
        elif zoom_reset_btn.collidepoint(pos):
            self.reset_zoom()
            return True
        elif zoom_in_btn.collidepoint(pos):
            self.zoom_in()
            return True
        
        return False
    
    def zoom_in(self):
        """Aumenta o zoom"""
        self.zoom_factor = min(self.max_zoom, self.zoom_factor * 1.2)
    
    def zoom_out(self):
        """Diminui o zoom"""
        self.zoom_factor = max(self.min_zoom, self.zoom_factor / 1.2)
    
    def reset_zoom(self):
        """Reseta o zoom para 1:1"""
        self.zoom_factor = 1.0
        self.zoom_offset = [0, 0]
    
    def screen_to_world(self, pos):
        """Converte coordenadas da tela para coordenadas do mundo (considerando zoom)"""
        world_x = (pos[0] - self.draw_area.x - self.zoom_offset[0]) / self.zoom_factor
        world_y = (pos[1] - self.draw_area.y - self.zoom_offset[1]) / self.zoom_factor
        return (int(world_x), int(world_y))
    
    def world_to_screen(self, pos):
        """Converte coordenadas do mundo para coordenadas da tela (considerando zoom)"""
        screen_x = pos[0] * self.zoom_factor + self.draw_area.x + self.zoom_offset[0]
        screen_y = pos[1] * self.zoom_factor + self.draw_area.y + self.zoom_offset[1]
        return (int(screen_x), int(screen_y))
    
    def handle_text_input(self, event):
        """Gerencia entrada de texto para ângulo de rotação e espessura"""
        # Input de rotação
        if self.rotation_input_active:
            if event.key == pygame.K_RETURN:
                try:
                    angle = float(self.rotation_input_text)
                    self.rotation_angle = angle % 360
                except ValueError:
                    pass
                self.rotation_input_active = False
                self.rotation_input_text = ""
                
            elif event.key == pygame.K_ESCAPE:
                self.rotation_input_active = False
                self.rotation_input_text = ""
                
            elif event.key == pygame.K_BACKSPACE:
                self.rotation_input_text = self.rotation_input_text[:-1]
                
            else:
                if event.unicode.isdigit() or event.unicode in '.-':
                    if len(self.rotation_input_text) < 10:
                        self.rotation_input_text += event.unicode
        
        # Input de espessura
        elif self.thickness_input_active:
            if event.key == pygame.K_RETURN:
                try:
                    thickness = int(self.thickness_input_text)
                    self.brush_thickness = max(1, min(50, thickness))
                except ValueError:
                    pass
                self.thickness_input_active = False
                self.thickness_input_text = ""
                
            elif event.key == pygame.K_ESCAPE:
                self.thickness_input_active = False
                self.thickness_input_text = ""
                
            elif event.key == pygame.K_BACKSPACE:
                self.thickness_input_text = self.thickness_input_text[:-1]
                
            else:
                if event.unicode.isdigit():
                    if len(self.thickness_input_text) < 3:
                        self.thickness_input_text += event.unicode
    
    def handle_scroll(self, direction, pos=None):
        """Manipula scroll do mouse para zoom ou ajustar valores"""
        keys = pygame.key.get_pressed()
        
        # Se Ctrl pressionado ou mouse na área de desenho, faz zoom
        if keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL] or (pos and self.draw_area.collidepoint(pos)):
            if direction > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            # Ajusta valores de transformação
            if self.transform_mode == TransformMode.ROTATE:
                self.rotation_angle += direction * 1
                self.rotation_angle = self.rotation_angle % 360
            else:
                self.transform_factor += direction * 0.05
                self.transform_factor = max(0.1, min(3.0, self.transform_factor))
    
    def handle_rotation_drag(self, current_pos):
        """Calcula rotação baseada no arrasto do mouse (mais fluida)"""
        if not self.rotation_start_pos:
            return
        
        # Calcula centroide das formas selecionadas
        selected_shapes = [s for s in self.shapes if s.selected]
        if not selected_shapes:
            return
        
        all_points = []
        for shape in selected_shapes:
            all_points.extend(shape.points)
        
        if not all_points:
            return
        
        cx = sum(p[0] for p in all_points) // len(all_points)
        cy = sum(p[1] for p in all_points) // len(all_points)
        
        # Converte centroide para coordenadas da tela
        center_screen = self.world_to_screen((cx, cy))
        
        # Calcula ângulo com mais precisão
        start_angle = math.degrees(math.atan2(
            self.rotation_start_pos[1] - center_screen[1], 
            self.rotation_start_pos[0] - center_screen[0]
        ))
        current_angle = math.degrees(math.atan2(
            current_pos[1] - center_screen[1], 
            current_pos[0] - center_screen[0]
        ))
        
        # Atualiza ângulo de rotação com suavização
        angle_diff = current_angle - start_angle
        self.rotation_angle = angle_diff % 360
    
    def point_in_rect(self, point, rect):
        """Verifica se um ponto está dentro de um retângulo"""
        return rect[0] <= point[0] <= rect[2] and rect[1] <= point[1] <= rect[3]
    
    def select_shapes(self, rect):
        """Seleciona formas dentro de um retângulo"""
        # Desmarca todas as formas
        for shape in self.shapes:
            shape.selected = False
        
        # Marca formas dentro do retângulo
        for shape in self.shapes:
            for point in shape.points:
                if self.point_in_rect(point, rect):
                    shape.selected = True
                    break
    
    def draw_line_dda(self, x1, y1, x2, y2, color):
        """Algoritmo DDA para rasterização de linhas"""
        dx = x2 - x1
        dy = y2 - y1
        steps = max(abs(dx), abs(dy))
        
        if steps == 0:
            return [(x1, y1)]
        
        x_inc = dx / steps
        y_inc = dy / steps
        
        points = []
        x, y = float(x1), float(y1)
        
        for _ in range(int(steps) + 1):
            points.append((int(round(x)), int(round(y))))
            x += x_inc
            y += y_inc
        
        return points
    
    def draw_line_bresenham(self, x1, y1, x2, y2, color):
        """Algoritmo de Bresenham para rasterização de linhas (otimizado)"""
        points = []
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        x, y = x1, y1
        
        while True:
            points.append((x, y))
            if x == x2 and y == y2:
                break
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        
        return points
    
    def draw_circle_bresenham(self, cx, cy, radius, color):
        """Algoritmo de Bresenham para círculos (otimizado)"""
        points = []
        x = 0
        y = radius
        d = 3 - 2 * radius
        
        while y >= x:
            # Desenha os 8 octantes
            octants = [
                (cx + x, cy + y), (cx - x, cy + y),
                (cx + x, cy - y), (cx - x, cy - y),
                (cx + y, cy + x), (cx - y, cy + x),
                (cx + y, cy - x), (cx - y, cy - x)
            ]
            points.extend(octants)
            
            x += 1
            if d > 0:
                y -= 1
                d = d + 4 * (x - y) + 10
            else:
                d = d + 4 * x + 6
        
        return points
    
    def apply_transformation_matrix(self, points, matrix):
        """Aplica matriz de transformação aos pontos (otimizado)"""
        result = []
        for x, y in points:
            # Converte para coordenadas homogêneas
            point = np.array([x, y, 1])
            # Aplica transformação
            transformed = np.dot(matrix, point)
            result.append((int(transformed[0]), int(transformed[1])))
        return result
    
    def get_translation_matrix(self, dx, dy):
        """Cria matriz de translação"""
        return np.array([
            [1, 0, dx],
            [0, 1, dy],
            [0, 0, 1]
        ])
    
    def get_rotation_matrix(self, angle, cx=0, cy=0):
        """Cria matriz de rotação em torno de um ponto"""
        cos_a = math.cos(math.radians(angle))
        sin_a = math.sin(math.radians(angle))
        return np.array([
            [cos_a, -sin_a, -cx*cos_a + cy*sin_a + cx],
            [sin_a, cos_a, -cx*sin_a - cy*cos_a + cy],
            [0, 0, 1]
        ])
    
    def get_scale_matrix(self, sx, sy, cx=0, cy=0):
        """Cria matriz de escala em torno de um ponto"""
        return np.array([
            [sx, 0, cx*(1-sx)],
            [0, sy, cy*(1-sy)],
            [0, 0, 1]
        ])
    
    def get_reflection_matrix(self, mode):
        """Cria matriz de reflexão (corrigida)"""
        if mode == TransformMode.REFLECT_X:
            # Reflexão no eixo X (espelha verticalmente)
            return np.array([
                [1, 0, 0],
                [0, -1, self.draw_area.height],  # Usa altura da área de desenho
                [0, 0, 1]
            ])
        elif mode == TransformMode.REFLECT_Y:
            # Reflexão no eixo Y (espelha horizontalmente) 
            return np.array([
                [-1, 0, self.draw_area.width],   # Usa largura da área de desenho
                [0, 1, 0],
                [0, 0, 1]
            ])
        else:  # REFLECT_XY
            # Reflexão nos dois eixos
            return np.array([
                [-1, 0, self.draw_area.width],
                [0, -1, self.draw_area.height],
                [0, 0, 1]
            ])
    
    def apply_transformations(self):
        """Aplica transformações às formas selecionadas"""
        selected_shapes = [s for s in self.shapes if s.selected]
        if not selected_shapes:
            return
        
        # Calcula centroide das formas selecionadas
        all_points = []
        for shape in selected_shapes:
            all_points.extend(shape.points)
        
        if not all_points:
            return
        
        cx = sum(p[0] for p in all_points) // len(all_points)
        cy = sum(p[1] for p in all_points) // len(all_points)
        
        # Cria matriz de transformação
        matrix = np.eye(3)
        
        if self.transform_mode == TransformMode.TRANSLATE:
            # Direções baseadas em botões ou posição do mouse
            keys = pygame.key.get_pressed()
            dx = dy = 0
            if keys[pygame.K_UP]: dy = -self.transform_factor * 20
            elif keys[pygame.K_DOWN]: dy = self.transform_factor * 20
            if keys[pygame.K_LEFT]: dx = -self.transform_factor * 20
            elif keys[pygame.K_RIGHT]: dx = self.transform_factor * 20
            
            # Se nenhuma tecla, usa posição do mouse
            if dx == 0 and dy == 0:
                mouse_pos = pygame.mouse.get_pos()
                dx = (mouse_pos[0] - 650) * 0.1
                dy = (mouse_pos[1] - 450) * 0.1
            
            matrix = self.get_translation_matrix(dx, dy)    
        
        # Aplica transformação
        for shape in selected_shapes:
            shape.points = self.apply_transformation_matrix(shape.points, matrix)
    
    def draw_shapes(self):
        """Desenha todas as formas na tela (com zoom)"""
        for shape in self.shapes:
            color = self.RED if shape.selected else shape.color
            thickness = max(1, int(shape.thickness * self.zoom_factor))
            
            if shape.type == 'point':
                # Converte coordenada para tela
                screen_pos = self.world_to_screen(shape.points[0])
                if self.draw_area.collidepoint(screen_pos):
                    point_size = max(2, int(5 * self.zoom_factor))
                    pygame.draw.circle(self.screen, color, screen_pos, point_size)
                    if shape.selected:
                        pygame.draw.circle(self.screen, self.WHITE, screen_pos, point_size + 2, 2)
            
            elif shape.type == 'line':
                if len(shape.points) >= 2:
                    start_pos = self.world_to_screen(shape.points[0])
                    end_pos = self.world_to_screen(shape.points[1])
                    
                    # Verifica se a linha está visível
                    if (self.draw_area.collidepoint(start_pos) or 
                        self.draw_area.collidepoint(end_pos)):
                        pygame.draw.line(self.screen, color, start_pos, end_pos, thickness)
                        
                        if shape.selected:
                            pygame.draw.line(self.screen, self.WHITE, start_pos, end_pos, thickness + 4)
                            pygame.draw.line(self.screen, color, start_pos, end_pos, thickness + 2)
            
            elif shape.type == 'circle':
                if len(shape.points) >= 2:
                    center_pos = self.world_to_screen(shape.points[0])
                    # Calcula raio considerando zoom
                    world_radius = math.sqrt((shape.points[1][0] - shape.points[0][0])**2 + 
                                           (shape.points[1][1] - shape.points[0][1])**2)
                    screen_radius = int(world_radius * self.zoom_factor)
                    
                    if screen_radius > 0:
                        pygame.draw.circle(self.screen, color, center_pos, screen_radius, thickness)
                        if shape.selected:
                            pygame.draw.circle(self.screen, self.WHITE, center_pos, screen_radius + 2, 2)
                            pygame.draw.circle(self.screen, color, center_pos, 4)
            
            elif shape.type == 'polygon':
                if len(shape.points) > 2:
                    screen_points = [self.world_to_screen(p) for p in shape.points]
                    # Verifica se algum ponto está visível
                    if any(self.draw_area.collidepoint(p) for p in screen_points):
                        pygame.draw.polygon(self.screen, color, screen_points, thickness)
                        
                        if shape.selected:
                            for i, point in enumerate(screen_points):
                                pygame.draw.circle(self.screen, self.WHITE, point, 6)
                                pygame.draw.circle(self.screen, color, point, 4)
            
            elif shape.type == 'freehand':
                if len(shape.points) > 1:
                    screen_points = []
                    for point in shape.points:
                        screen_pos = self.world_to_screen(point)
                        if self.draw_area.collidepoint(screen_pos):
                            screen_points.append(screen_pos)
                    
                    if len(screen_points) > 1:
                        # Desenha linha suave conectando pontos
                        for i in range(len(screen_points) - 1):
                            pygame.draw.line(self.screen, color, 
                                           screen_points[i], screen_points[i + 1], thickness)
                        
                        # Desenha pontos para suavizar
                        for point in screen_points:
                            pygame.draw.circle(self.screen, color, point, thickness // 2)
        
        # Desenha polígono em construção
        if self.current_polygon:
            screen_polygon = [self.world_to_screen(p) for p in self.current_polygon]
            animation_offset = math.sin(pygame.time.get_ticks() * 0.01) * 2
            
            for i, point in enumerate(screen_polygon):
                if self.draw_area.collidepoint(point):
                    animated_pos = (point[0], int(point[1] + animation_offset))
                    pygame.draw.circle(self.screen, self.ACCENT, animated_pos, 6)
                    pygame.draw.circle(self.screen, self.WHITE, point, 8, 2)
                    
                    # Número do vértice
                    num_text = self.font_small.render(str(i + 1), True, self.WHITE)
                    num_bg = pygame.Rect(point[0] - 8, point[1] - 20, 16, 16)
                    pygame.draw.rect(self.screen, self.ACCENT, num_bg, border_radius=8)
                    self.screen.blit(num_text, (point[0] - 4, point[1] - 18))
            
            # Conecta pontos
            for i in range(len(screen_polygon) - 1):
                if (self.draw_area.collidepoint(screen_polygon[i]) and 
                    self.draw_area.collidepoint(screen_polygon[i + 1])):
                    pygame.draw.line(self.screen, self.ACCENT, 
                                   screen_polygon[i], screen_polygon[i + 1], 4)
        
        # Desenha desenho livre em construção
        if self.current_freehand and len(self.current_freehand) > 1:
            screen_freehand = [self.world_to_screen(p) for p in self.current_freehand]
            screen_freehand = [p for p in screen_freehand if self.draw_area.collidepoint(p)]
            
            if len(screen_freehand) > 1:
                thickness = max(1, int(self.brush_thickness * self.zoom_factor))
                for i in range(len(screen_freehand) - 1):
                    pygame.draw.line(self.screen, self.current_draw_color,
                                   screen_freehand[i], screen_freehand[i + 1], thickness)
                
                # Desenha pontos para suavizar
                for point in screen_freehand:
                    pygame.draw.circle(self.screen, self.current_draw_color, point, thickness // 2)
        
        # Desenha retângulo de seleção
        if self.selection_rect:
            # Fundo transparente
            selection_surface = pygame.Surface((self.selection_rect.width, self.selection_rect.height))
            selection_surface.set_alpha(30)
            selection_surface.fill(self.ACCENT)
            self.screen.blit(selection_surface, self.selection_rect.topleft)
            
            # Borda animada
            border_offset = math.sin(pygame.time.get_ticks() * 0.01) * 2
            animated_rect = pygame.Rect(
                self.selection_rect.x - border_offset,
                self.selection_rect.y - border_offset,
                self.selection_rect.width + 2 * border_offset,
                self.selection_rect.height + 2 * border_offset
            )
            pygame.draw.rect(self.screen, self.ACCENT, animated_rect, 3)
            pygame.draw.rect(self.screen, self.WHITE, self.selection_rect, 1)
    
    def run(self):
        """Loop principal do programa (otimizado para fluidez)"""
        running = True
        mouse_pressed = False
        
        while running:
            # Processa eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                elif event.type == pygame.KEYDOWN:
                    # Gerencia entrada de texto primeiro
                    if self.rotation_input_active or self.thickness_input_active:
                        self.handle_text_input(event)
                        continue
                    
                    # Atalhos de teclado
                    if event.key == pygame.K_c:
                        self.shapes = []
                        self.current_polygon = []
                        self.current_freehand = []
                    elif event.key == pygame.K_ESCAPE:
                        if self.current_polygon:
                            if len(self.current_polygon) >= 3:
                                self.shapes.append(Shape('polygon', self.current_polygon.copy(), 
                                                       self.current_draw_color, self.brush_thickness))
                            self.current_polygon = []
                        elif self.current_freehand:
                            if len(self.current_freehand) > 1:
                                self.shapes.append(Shape('freehand', self.current_freehand.copy(), 
                                                       self.current_draw_color, self.brush_thickness))
                            self.current_freehand = []
                            self.drawing_freehand = False
                    elif event.key == pygame.K_RETURN:
                        self.apply_transformations()
                        if self.transform_mode == TransformMode.ROTATE:
                            self.rotation_angle = 0.0
                    elif pygame.K_1 <= event.key <= pygame.K_9:
                        value = event.key - pygame.K_0
                        if self.transform_mode == TransformMode.ROTATE:
                            self.rotation_angle = value * 10
                        else:
                            self.transform_factor = value * 0.2 + 0.1  # 0.3, 0.5, 0.7, ... 1.9
                    
                    # Atalhos de zoom
                    keys = pygame.key.get_pressed()
                    if keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]:
                        if event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                            self.zoom_in()
                        elif event.key == pygame.K_MINUS:
                            self.zoom_out()
                        elif event.key == pygame.K_0:
                            self.reset_zoom()
                
                elif event.type == pygame.MOUSEWHEEL:
                    # Controle de zoom e valores
                    self.handle_scroll(event.y, pygame.mouse.get_pos())
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Botão esquerdo
                        pos = pygame.mouse.get_pos()
                        
                        # Desativa inputs se clicar fora
                        if self.rotation_input_active or self.thickness_input_active:
                            # Verifica se clicou nos campos de input
                            thickness_input_rect = pygame.Rect(150, 235, 80, 25)
                            rotation_input_rect = pygame.Rect(25, 655, 200, 25)
                            
                            if not (thickness_input_rect.collidepoint(pos) or 
                                   rotation_input_rect.collidepoint(pos)):
                                self.rotation_input_active = False
                                self.thickness_input_active = False
                        
                        # Verifica clique no painel
                        if self.handle_panel_click(pos):
                            continue
                        
                        # Verifica se está na área de desenho
                        if not self.draw_area.collidepoint(pos):
                            continue
                        
                        # Converte posição para coordenadas do mundo
                        world_pos = self.screen_to_world(pos)
                        
                        # Modo seleção
                        if self.draw_mode == DrawMode.SELECT:
                            selected_shapes = [s for s in self.shapes if s.selected]
                            
                            if self.transform_mode == TransformMode.ROTATE and selected_shapes:
                                self.rotating = True
                                self.rotation_start_pos = pos
                            else:
                                self.selecting = True
                                self.selection_start = pos
                            mouse_pressed = True
                        
                        # Desenho de formas
                        elif self.draw_mode == DrawMode.POINT:
                            self.shapes.append(Shape('point', [world_pos], self.current_draw_color, self.brush_thickness))
                        
                        elif self.draw_mode == DrawMode.LINE:
                            if not hasattr(self, 'line_start'):
                                self.line_start = world_pos
                            else:
                                self.shapes.append(Shape('line', [self.line_start, world_pos], 
                                                       self.current_draw_color, self.brush_thickness))
                                delattr(self, 'line_start')
                        
                        elif self.draw_mode == DrawMode.CIRCLE:
                            if not hasattr(self, 'circle_center'):
                                self.circle_center = world_pos
                            else:
                                self.shapes.append(Shape('circle', [self.circle_center, world_pos], 
                                                       self.current_draw_color, self.brush_thickness))
                                delattr(self, 'circle_center')
                        
                        elif self.draw_mode == DrawMode.POLYGON:
                            self.current_polygon.append(world_pos)
                        
                        elif self.draw_mode == DrawMode.FREEHAND:
                            self.drawing_freehand = True
                            self.current_freehand = [world_pos]
                            mouse_pressed = True
                
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        if self.rotating:
                            self.apply_transformations()
                            self.rotation_angle = 0.0
                            self.rotating = False
                            self.rotation_start_pos = None
                        elif self.selecting:
                            self.selecting = False
                            if self.selection_rect:
                                # Converte retângulo para coordenadas do mundo
                                world_rect = (
                                    self.screen_to_world((self.selection_rect.left, self.selection_rect.top))[0],
                                    self.screen_to_world((self.selection_rect.left, self.selection_rect.top))[1],
                                    self.screen_to_world((self.selection_rect.right, self.selection_rect.bottom))[0],
                                    self.screen_to_world((self.selection_rect.right, self.selection_rect.bottom))[1]
                                )
                                self.select_shapes(world_rect)
                                self.selection_rect = None
                        elif self.drawing_freehand:
                            if len(self.current_freehand) > 1:
                                self.shapes.append(Shape('freehand', self.current_freehand.copy(), self.current_draw_color, self.brush_thickness))
                            self.current_freehand = []
                            self.drawing_freehand = False
                        mouse_pressed = False
                
                elif event.type == pygame.MOUSEMOTION:
                    if mouse_pressed:
                        current_pos = pygame.mouse.get_pos()
                        
                        if self.rotating:
                            self.handle_rotation_drag(current_pos)
                        elif self.selecting:
                            self.selection_rect = pygame.Rect(
                                min(self.selection_start[0], current_pos[0]),
                                min(self.selection_start[1], current_pos[1]),
                                abs(current_pos[0] - self.selection_start[0]),
                                abs(current_pos[1] - self.selection_start[1])
                            )
                        elif self.drawing_freehand:
                            world_pos = self.screen_to_world(current_pos)
                            if self.draw_area.collidepoint(current_pos):
                                # Adiciona ponto apenas se estiver longe o suficiente do último
                                if (not self.current_freehand or 
                                    math.sqrt((world_pos[0] - self.current_freehand[-1][0])**2 + 
                                             (world_pos[1] - self.current_freehand[-1][1])**2) > 3):
                                    self.current_freehand.append(world_pos)
            
            # Renderização
            self.screen.fill(self.WHITE)
            
            # Área de desenho com sombra e zoom info
            shadow_rect = pygame.Rect(self.draw_area.x + 3, self.draw_area.y + 3, 
                                    self.draw_area.width, self.draw_area.height)
            pygame.draw.rect(self.screen, (230, 230, 230), shadow_rect)
            pygame.draw.rect(self.screen, self.WHITE, self.draw_area)
            pygame.draw.rect(self.screen, self.DARK_GRAY, self.draw_area, 3)
            
            # Mostra informações de zoom na área de desenho
            if self.zoom_factor != 1.0:
                zoom_info = f"Zoom: {self.zoom_factor:.1f}x"
                zoom_text = self.font_small.render(zoom_info, True, self.DARK_GRAY)
                zoom_bg = pygame.Rect(self.draw_area.right - 100, self.draw_area.top + 10, 80, 20)
                pygame.draw.rect(self.screen, (255, 255, 255, 200), zoom_bg, border_radius=5)
                self.screen.blit(zoom_text, (zoom_bg.x + 5, zoom_bg.y + 3))
            
            # Desenha formas e interface
            self.draw_shapes()
            self.draw_interface()
            
            # Preview de formas em construção
            if hasattr(self, 'line_start'):
                mouse_pos = pygame.mouse.get_pos()
                if self.draw_area.collidepoint(mouse_pos):
                    start_screen = self.world_to_screen(self.line_start)
                    thickness = max(1, int(self.brush_thickness * self.zoom_factor))
                    pygame.draw.line(self.screen, (*self.current_draw_color, 128), 
                                   start_screen, mouse_pos, thickness)
            
            if hasattr(self, 'circle_center'):
                mouse_pos = pygame.mouse.get_pos()
                if self.draw_area.collidepoint(mouse_pos):
                    center_screen = self.world_to_screen(self.circle_center)
                    world_mouse = self.screen_to_world(mouse_pos)
                    radius = int(math.sqrt((world_mouse[0] - self.circle_center[0])**2 + 
                                         (world_mouse[1] - self.circle_center[1])**2) * self.zoom_factor)
                    thickness = max(1, int(self.brush_thickness * self.zoom_factor))
                    if radius > 0:
                        pygame.draw.circle(self.screen, (*self.current_draw_color, 128), 
                                         center_screen, radius, thickness)
            
            # Atualiza display
            pygame.display.flip()
            self.clock.tick(self.fps)
        
        pygame.quit()

if __name__ == "__main__":
    app = PaintCG()
    app.run()