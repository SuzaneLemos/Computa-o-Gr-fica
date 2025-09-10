import pygame
import numpy as np
import math
from enum import Enum
import colorsys

# --- ENUMS para Modos e Algoritmos ---
class DrawMode(Enum):
    SELECT = 0
    POINT = 1
    LINE = 2
    CIRCLE = 3
    POLYGON = 4
    FREEHAND = 5
    CUT = 6 # Adicionada nova ferramenta

class TransformMode(Enum):
    TRANSLATE = 0
    ROTATE = 1
    SCALE = 2
    REFLECT_X = 3
    REFLECT_Y = 4
    REFLECT_XY = 5

class LineAlgorithm(Enum):
    BRESENHAM = 0
    DDA = 1

# --- Classe para Formas Geométricas ---
class Shape:
    def __init__(self, shape_type, points, color=(0, 0, 0), thickness=2):
        self.type = shape_type
        self.points = np.array(points, dtype=float)
        self.color = color
        self.thickness = thickness
        self.selected = False

# --- Classe da Roda de Cores ---
class ColorWheel:
    def __init__(self, center, radius):
        self.center = center
        self.radius = radius
        self.wheel_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        self.create_wheel()

    def create_wheel(self):
        for x in range(self.radius * 2):
            for y in range(self.radius * 2):
                dx, dy = x - self.radius, y - self.radius
                distance = math.sqrt(dx**2 + dy**2)
                if distance <= self.radius:
                    angle = math.atan2(dy, dx)
                    hue = (angle + math.pi) / (2 * math.pi)
                    saturation = distance / self.radius
                    rgb = colorsys.hsv_to_rgb(hue, saturation, 1.0)
                    color = tuple(int(c * 255) for c in rgb)
                    self.wheel_surface.set_at((x, y), color)

    def get_color_at_pos(self, pos):
        dx, dy = pos[0] - self.center[0], pos[1] - self.center[1]
        distance = math.sqrt(dx**2 + dy**2)
        if distance <= self.radius:
            angle = math.atan2(dy, dx)
            hue = (angle + math.pi) / (2 * math.pi)
            saturation = distance / self.radius
            rgb = colorsys.hsv_to_rgb(hue, saturation, 1.0)
            return tuple(int(c * 255) for c in rgb)
        return None

    def draw(self, screen):
        screen.blit(self.wheel_surface, (self.center[0] - self.radius, self.center[1] - self.radius))
        pygame.draw.circle(screen, (100, 100, 100), self.center, self.radius, 2)

# --- Classe Principal do Paint ---
class PaintCG:
    def __init__(self):
        pygame.init()
        self.width, self.height = 1300, 900
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        pygame.display.set_caption("Paint Pro - Computação Gráfica")

        # Paleta de Cores
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.BLUE = (52, 152, 219)
        self.DARK_BLUE = (41, 128, 185)
        self.GREEN = (46, 204, 113)
        self.RED = (231, 76, 60)
        self.ORANGE = (230, 126, 34)
        self.PURPLE = (155, 89, 182)
        self.GRAY = (149, 165, 166)
        self.LIGHT_GRAY = (236, 240, 241)
        self.DARK_GRAY = (52, 73, 94)
        self.ACCENT = (26, 188, 156)
        
        # Estado do programa
        self.shapes = []
        self.current_polygon = []
        self.temp_points = []
        self.draw_mode = DrawMode.SELECT
        self.transform_mode = TransformMode.TRANSLATE
        self.line_algorithm = LineAlgorithm.BRESENHAM
        
        # UI
        self.font_title = pygame.font.Font(None, 28)
        self.font_button = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 18)
        self.font_tiny = pygame.font.Font(None, 15)
        self.panel_width = 320
        self.update_draw_area()
        self.ui_elements = {}

        # Variáveis de interação
        self.mouse_pressed = False
        self.action_in_progress = False
        self.drag_start_pos = None

        # Transformação
        self.transform_factor = 1.0
        self.rotation_angle = 0.0
        self.rotation_input_active = False
        self.rotation_input_text = ""

        # Desenho
        self.brush_thickness = 2
        self.thickness_input_active = False
        self.thickness_input_text = ""
        self.current_draw_color = self.BLACK
        
        # Zoom e Pan
        self.zoom_factor = 1.0
        self.pan_offset = np.array([0.0, 0.0])
        self.panning = False
        
        self.color_wheel = ColorWheel((100, 110), 60)
        self.clock = pygame.time.Clock()

        # --- Adicionado para Scroll ---
        self.panel_scroll_y = 0
        self.panel_content_height = self.height 
        self.dragging_scrollbar = False
        self.scrollbar_grabber_offset_y = 0

    def update_draw_area(self):
        self.width, self.height = self.screen.get_size()
        self.draw_area = pygame.Rect(self.panel_width, 0, self.width - self.panel_width, self.height)

    # --- Funções de Coordenadas ---
    def screen_to_world(self, pos):
        return (np.array(pos) - np.array(self.draw_area.topleft) - self.pan_offset) / self.zoom_factor

    def world_to_screen(self, pos):
        return (np.array(pos) * self.zoom_factor + self.pan_offset + np.array(self.draw_area.topleft)).astype(int)

    # --- Algoritmos de Rasterização ---
    def rasterize_line_dda(self, p1, p2):
        x1, y1 = p1; x2, y2 = p2
        dx, dy = x2 - x1, y2 - y1
        steps = max(abs(dx), abs(dy))
        if steps == 0: return [(int(x1), int(y1))]
        x_inc, y_inc = dx / steps, dy / steps
        x, y = float(x1), float(y1)
        points = []
        for _ in range(int(steps) + 1):
            points.append((round(x), round(y))); x += x_inc; y += y_inc
        return points

    def rasterize_line_bresenham(self, p1, p2):
        x1, y1 = int(p1[0]), int(p1[1]); x2, y2 = int(p2[0]), int(p2[1])
        points = []
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        sx = 1 if x1 < x2 else -1; sy = 1 if y1 < y2 else -1
        err = dx - dy
        while True:
            points.append((x1, y1))
            if x1 == x2 and y1 == y2: break
            e2 = 2 * err
            if e2 > -dy: err -= dy; x1 += sx
            if e2 < dx: err += dx; y1 += sy
        return points

    def rasterize_circle_bresenham(self, center, radius):
        cx, cy = int(center[0]), int(center[1]); radius = int(radius)
        points = []; x, y = 0, radius; d = 3 - 2 * radius
        while y >= x:
            points.extend([(cx+x,cy+y),(cx-x,cy+y),(cx+x,cy-y),(cx-x,cy-y),(cx+y,cy+x),(cx-y,cy+x),(cx+y,cy-x),(cx-y,cy-x)])
            x += 1
            if d > 0: y -= 1; d += 4 * (x - y) + 10
            else: d += 4 * x + 6
        return points

    # --- Algoritmos de Recorte/Corte ---
    def liang_barsky_clip_params(self, p1, p2, rect):
        x1, y1 = p1; x2, y2 = p2
        xmin, ymin, xmax, ymax = rect.left, rect.top, rect.right, rect.bottom
        dx, dy = x2 - x1, y2 - y1
        p = [-dx, dx, -dy, dy]; q = [x1 - xmin, xmax - x1, y1 - ymin, ymax - y1]
        u1, u2 = 0.0, 1.0
        for i in range(4):
            if abs(p[i]) < 1e-6: # Perto de zero
                if q[i] < 0: return None # Paralela e fora
            else:
                t = q[i] / p[i]
                if p[i] < 0: u1 = max(u1, t)
                else: u2 = min(u2, t)
        if u1 > u2: return None # Linha completamente fora
        return u1, u2

    def split_line_with_rect(self, p1, p2, rect):
        """Retorna uma lista de segmentos de linha que estão FORA do retângulo de corte."""
        params = self.liang_barsky_clip_params(p1, p2, rect)
        
        # Caso 1: Linha não cruza o retângulo (está totalmente fora)
        if params is None:
            return [np.array([p1, p2])]
            
        u1, u2 = params
        
        # Caso 2: Linha está totalmente dentro do retângulo, é removida
        if u1 <= 0.0001 and u2 >= 0.9999:
            return []

        segments = []
        delta = p2 - p1
        
        # Adiciona o segmento antes do ponto de entrada (se houver)
        if u1 > 0.0001:
            segments.append(np.array([p1, p1 + u1 * delta]))

        # Adiciona o segmento depois do ponto de saída (se houver)
        if u2 < 0.9999:
            segments.append(np.array([p1 + u2 * delta, p2]))
            
        return segments

    # --- Funções de Transformação ---
    def get_transform_matrix(self, shape_centroid):
        cx, cy = shape_centroid
        sx = sy = self.transform_factor
        angle_rad = math.radians(self.rotation_angle)
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        to_origin = np.array([[1, 0, -cx], [0, 1, -cy], [0, 0, 1]])
        from_origin = np.array([[1, 0, cx], [0, 1, cy], [0, 0, 1]])
        if self.transform_mode == TransformMode.ROTATE:
            rot = np.array([[cos_a, -sin_a, 0], [sin_a, cos_a, 0], [0, 0, 1]])
            return from_origin @ rot @ to_origin
        if self.transform_mode == TransformMode.SCALE:
            scale = np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1]])
            return from_origin @ scale @ to_origin
        reflect_map = {
            TransformMode.REFLECT_X: np.array([[1, 0, 0], [0, -1, 0], [0, 0, 1]]),
            TransformMode.REFLECT_Y: np.array([[-1, 0, 0], [0, 1, 0], [0, 0, 1]]),
            TransformMode.REFLECT_XY: np.array([[-1, 0, 0], [0, -1, 0], [0, 0, 1]])
        }
        if self.transform_mode in reflect_map:
            return from_origin @ reflect_map[self.transform_mode] @ to_origin
        return np.identity(3)

    def apply_matrix_to_points(self, points, matrix):
        points_h = np.hstack([points, np.ones((points.shape[0], 1))])
        transformed_h = (matrix @ points_h.T).T
        return transformed_h[:, :2]

    # --- Lógica de UI ---
    def draw_ui(self):
        self.ui_elements.clear()
        
        panel_content_clip_rect = pygame.Rect(0, 0, self.panel_width, self.height)
        pygame.draw.rect(self.screen, self.LIGHT_GRAY, panel_content_clip_rect)
        self.screen.set_clip(panel_content_clip_rect)

        y_offset = -self.panel_scroll_y
        
        y = 20
        title = self.font_title.render("Paint PRO", True, self.DARK_BLUE)
        self.screen.blit(title, (20, y + y_offset))
        pygame.draw.line(self.screen, self.DARK_BLUE, (20, y + 25 + y_offset), (self.panel_width - 20, y + 25 + y_offset), 1)
        y += 40

        self.screen.blit(self.font_button.render("Cor:", True, self.DARK_GRAY), (20, y + y_offset))
        self.color_wheel.center = (100, y + 70 + y_offset)
        self.color_wheel.draw(self.screen)
        pygame.draw.rect(self.screen, self.current_draw_color, (180, y + 50 + y_offset, 40, 40), border_radius=8)
        pygame.draw.rect(self.screen, self.DARK_GRAY, (180, y + 50 + y_offset, 40, 40), 2, border_radius=8)
        y += 140

        self.screen.blit(self.font_button.render("Espessura:", True, self.DARK_GRAY), (20, y + y_offset))
        self.ui_elements['thickness_dec'] = self.draw_plus_minus_button(125, y, "-", self.RED, y_offset)
        self.ui_elements['thickness_inc'] = self.draw_plus_minus_button(125, y - 13, "+", self.GREEN, y_offset)
        self.ui_elements['thickness_input'] = self.draw_text_input(150, y-5, 80, self.thickness_input_text, self.brush_thickness, self.thickness_input_active, y_offset)
        y += 40
        
        y = self.draw_button_section("Ferramentas:", DrawMode, self.draw_mode, y, {DrawMode.SELECT: self.ACCENT, DrawMode.POINT: self.BLUE, DrawMode.LINE: self.GREEN, DrawMode.CIRCLE: self.RED, DrawMode.POLYGON: self.PURPLE, DrawMode.FREEHAND: self.ORANGE, DrawMode.CUT: self.DARK_GRAY}, y_offset)
        y = self.draw_button_section("Transformações:", TransformMode, self.transform_mode, y, {TransformMode.TRANSLATE: self.BLUE, TransformMode.ROTATE: self.GREEN, TransformMode.SCALE: self.ORANGE, TransformMode.REFLECT_X: self.RED, TransformMode.REFLECT_Y: self.PURPLE, TransformMode.REFLECT_XY: self.ACCENT}, y_offset)
        y = self.draw_button_section("Rasterização:", LineAlgorithm, self.line_algorithm, y, {LineAlgorithm.BRESENHAM: self.BLUE, LineAlgorithm.DDA: self.GREEN}, y_offset)

        y = self.draw_controls_section(y, y_offset)
        y += 150

        self.screen.blit(self.font_button.render("Zoom da Tela:", True, self.DARK_GRAY), (20, y + y_offset))
        self.ui_elements['zoom_out'] = self.draw_zoom_button(20, y+25, "−", self.RED, y_offset)
        self.ui_elements['zoom_reset'] = self.draw_zoom_button(90, y+25, "1:1", self.BLUE, y_offset)
        self.ui_elements['zoom_in'] = self.draw_zoom_button(160, y+25, "+", self.GREEN, y_offset)
        self.screen.blit(self.font_small.render(f"Zoom: {self.zoom_factor:.1f}x", True, self.DARK_GRAY), (230, y + 32 + y_offset))
        y += 65

        self.screen.blit(self.font_tiny.render("Atalhos: C (Limpar) - Esc (Finalizar)", True, self.DARK_BLUE), (20, self.height - 25))
        
        self.panel_content_height = y

        self.screen.set_clip(None)

        pygame.draw.line(self.screen, self.DARK_GRAY, (self.panel_width - 2, 0), (self.panel_width - 2, self.height), 2)
        
        if self.panel_content_height > self.height:
            self.draw_scrollbar()


    def draw_button_section(self, title, enum_class, active_mode, y_start, colors, y_offset):
        self.screen.blit(self.font_button.render(title, True, self.DARK_GRAY), (20, y_start + y_offset))
        y = y_start + 25
        for mode in enum_class:
            is_active = (mode == active_mode)
            color = colors.get(mode, self.BLUE)
            self.ui_elements[mode] = self.draw_styled_button(y, mode.name.replace('_', ' '), color, is_active, y_offset)
            y += 35
        return y + 5
        
    def draw_styled_button(self, y, text, color, is_active, y_offset):
        rect_visual = pygame.Rect(20, y + y_offset, self.panel_width - 40, 30)
        btn_color = color if is_active else self.WHITE
        text_color = self.WHITE if is_active else color
        pygame.draw.rect(self.screen, btn_color, rect_visual, border_radius=8)
        pygame.draw.rect(self.screen, color, rect_visual, 2, border_radius=8)
        text_surf = self.font_button.render(text, True, text_color)
        self.screen.blit(text_surf, text_surf.get_rect(center=rect_visual.center))
        return pygame.Rect(20, y, self.panel_width - 40, 30)
        
    def draw_plus_minus_button(self, x, y, text, color, y_offset):
        rect_visual = pygame.Rect(x, y + y_offset, 20, 12)
        pygame.draw.rect(self.screen, color, rect_visual, border_radius=3)
        text_surf = pygame.font.Font(None, 16).render(text, True, self.WHITE)
        self.screen.blit(text_surf, text_surf.get_rect(center=rect_visual.center))
        return pygame.Rect(x, y, 20, 12)

    def draw_text_input(self, x, y, w, text, value, is_active, y_offset):
        rect_visual = pygame.Rect(x, y + y_offset, w, 25)
        input_color = self.ACCENT if is_active else self.WHITE
        pygame.draw.rect(self.screen, input_color, rect_visual, border_radius=5)
        pygame.draw.rect(self.screen, self.DARK_GRAY, rect_visual, 2, border_radius=5)
        display_text = text if is_active else str(value)
        text_surf = self.font_small.render(display_text, True, self.BLACK)
        self.screen.blit(text_surf, (rect_visual.x + 5, rect_visual.y + 5))
        if is_active and pygame.time.get_ticks() % 1000 < 500:
            cursor_x = rect_visual.x + 5 + text_surf.get_width()
            pygame.draw.line(self.screen, self.BLACK, (cursor_x, rect_visual.y + 3), (cursor_x, rect_visual.y + 22), 1)
        return pygame.Rect(x, y, w, 25)

    def draw_zoom_button(self, x, y, text, color, y_offset):
        rect_visual = pygame.Rect(x, y + y_offset, 60, 25)
        pygame.draw.rect(self.screen, color, rect_visual, border_radius=5)
        text_surf = self.font_small.render(text, True, self.WHITE)
        self.screen.blit(text_surf, text_surf.get_rect(center=rect_visual.center))
        return pygame.Rect(x, y, 60, 25)
        
    def draw_controls_section(self, y, y_offset):
        control_bg_visual = pygame.Rect(15, y + y_offset, self.panel_width - 30, 140)
        pygame.draw.rect(self.screen, self.WHITE, control_bg_visual, border_radius=12)
        pygame.draw.rect(self.screen, self.DARK_BLUE, control_bg_visual, 2, border_radius=12)
        self.screen.blit(self.font_button.render("Controles:", True, self.DARK_BLUE), (25, y + 10 + y_offset))
        y_inner = y + 25
        if self.transform_mode == TransformMode.ROTATE:
            self.screen.blit(self.font_small.render("Ângulo:", True, self.DARK_GRAY), (25, y_inner + 15 + y_offset))
            self.ui_elements['rotation_input'] = self.draw_text_input(100, y_inner + 10, 100, self.rotation_input_text, int(self.rotation_angle), self.rotation_input_active, y_offset)
            self.screen.blit(self.font_tiny.render("Pressione Enter para aplicar", True, self.GRAY), (25, y_inner + 80 + y_offset))
        else:
            self.screen.blit(self.font_small.render(f"Fator: {self.transform_factor:.2f}", True, self.DARK_GRAY), (25, y_inner + 15 + y_offset))
            progress_bg = pygame.Rect(25, y_inner + 40 + y_offset, 200, 12)
            pygame.draw.rect(self.screen, self.LIGHT_GRAY, progress_bg, border_radius=6)
            progress = np.clip((self.transform_factor - 0.1) / 2.9, 0, 1)
            progress_rect = pygame.Rect(25, y_inner + 40 + y_offset, int(progress * 200), 12)
            bar_color = self.RED if self.transform_factor < 1.0 else (self.GREEN if self.transform_factor > 1.0 else self.BLUE)
            pygame.draw.rect(self.screen, bar_color, progress_rect, border_radius=6)
            self.ui_elements['factor_dec'] = self.draw_plus_minus_button(240, y_inner + 40, "-", self.RED, y_offset)
            self.ui_elements['factor_inc'] = self.draw_plus_minus_button(265, y_inner + 40, "+", self.GREEN, y_offset)
            self.screen.blit(self.font_tiny.render("Use scroll no painel para ajustar", True, self.GRAY), (25, y_inner + 80 + y_offset))
            self.screen.blit(self.font_tiny.render("Pressione Enter para aplicar", True, self.GRAY), (25, y_inner + 95 + y_offset))
        return y

    def draw_scrollbar(self):
        if self.panel_content_height <= self.height:
            return
        track_rect = pygame.Rect(self.panel_width - 10, 5, 8, self.height - 10)
        pygame.draw.rect(self.screen, self.GRAY, track_rect, border_radius=4)
        visible_ratio = self.height / self.panel_content_height
        grabber_height = max(25, self.height * visible_ratio)
        scrollable_height = self.panel_content_height - self.height
        scroll_ratio = self.panel_scroll_y / scrollable_height if scrollable_height > 0 else 0
        track_inner_height = track_rect.height - grabber_height
        grabber_y = track_rect.y + track_inner_height * scroll_ratio
        grabber_rect = pygame.Rect(track_rect.x, grabber_y, 8, grabber_height)
        pygame.draw.rect(self.screen, self.DARK_GRAY, grabber_rect, border_radius=4)
        self.ui_elements['scrollbar_grabber'] = grabber_rect

    # --- Lógica de Desenho na Tela ---
    def draw_canvas(self):
        pygame.draw.rect(self.screen, self.WHITE, self.draw_area)
        for shape in self.shapes:
            color = shape.color
            algo = self.rasterize_line_bresenham if self.line_algorithm == LineAlgorithm.BRESENHAM else self.rasterize_line_dda
            
            if shape.type == 'point':
                if self.draw_area.collidepoint(self.world_to_screen(shape.points[0])):
                    pygame.draw.circle(self.screen, color, self.world_to_screen(shape.points[0]), shape.thickness + 2)
            elif shape.type == 'line':
                for p in algo(shape.points[0], shape.points[1]): self.draw_pixel_thick(self.world_to_screen(p), color, shape.thickness)
            elif shape.type == 'circle':
                radius = np.linalg.norm(shape.points[1] - shape.points[0])
                for p in self.rasterize_circle_bresenham(shape.points[0], radius): self.draw_pixel_thick(self.world_to_screen(p), color, shape.thickness)
            elif shape.type == 'polygon':
                for i in range(len(shape.points)):
                    for p in algo(shape.points[i], shape.points[(i+1)%len(shape.points)]): self.draw_pixel_thick(self.world_to_screen(p), color, shape.thickness)
            elif shape.type == 'freehand':
                for i in range(len(shape.points) - 1):
                    for p in algo(shape.points[i], shape.points[i+1]): self.draw_pixel_thick(self.world_to_screen(p), color, shape.thickness)

            if shape.selected:
                points_to_mark = shape.points
                if len(shape.points) > 20:
                    step = len(shape.points) // 10
                    points_to_mark = shape.points[::step]
                
                for point in points_to_mark:
                    screen_pos = self.world_to_screen(point)
                    if self.draw_area.collidepoint(screen_pos):
                        pygame.draw.circle(self.screen, shape.color, screen_pos, 6)
        
        if self.action_in_progress and self.temp_points:
            mouse_pos = pygame.mouse.get_pos()
            if self.draw_mode == DrawMode.LINE: pygame.draw.line(self.screen, self.GRAY, self.world_to_screen(self.temp_points[0]), mouse_pos, 1)
            elif self.draw_mode == DrawMode.CIRCLE: pygame.draw.circle(self.screen, self.GRAY, self.world_to_screen(self.temp_points[0]), int(np.linalg.norm(np.array(mouse_pos) - self.world_to_screen(self.temp_points[0]))), 1)
            elif self.draw_mode == DrawMode.POLYGON and self.current_polygon:
                 points_screen = [self.world_to_screen(p) for p in self.current_polygon]
                 if len(points_screen) > 1: pygame.draw.lines(self.screen, self.GRAY, False, points_screen, 1)
                 pygame.draw.line(self.screen, self.GRAY, points_screen[-1], mouse_pos, 1)
        
        elif self.mouse_pressed and self.drag_start_pos and self.draw_mode in [DrawMode.SELECT, DrawMode.CUT]:
            rect = pygame.Rect(self.drag_start_pos, (pygame.mouse.get_pos()[0] - self.drag_start_pos[0], pygame.mouse.get_pos()[1] - self.drag_start_pos[1])); rect.normalize()
            preview_color = self.RED if self.draw_mode == DrawMode.CUT else self.ACCENT
            pygame.draw.rect(self.screen, preview_color, rect, 1)
            
        pygame.draw.rect(self.screen, self.GRAY, self.draw_area, 1)

    def draw_pixel_thick(self, pos, color, thickness):
        if not self.draw_area.collidepoint(pos): return
        r = int(thickness * self.zoom_factor / 2)
        if r < 1:
            if self.draw_area.collidepoint(pos): self.screen.set_at(pos, color)
        else:
            pygame.draw.circle(self.screen, color, pos, r)

    # --- Lógica de Eventos ---
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return False
            if event.type == pygame.VIDEORESIZE: self.update_draw_area()
            if self.rotation_input_active or self.thickness_input_active:
                 if event.type == pygame.KEYDOWN: self.handle_text_input(event); continue
            self.handle_mouse_events(event)
            self.handle_keyboard_events(event)
        return True

    def handle_text_input(self, event):
        target_text = "rotation_input_text" if self.rotation_input_active else "thickness_input_text"
        if event.key == pygame.K_RETURN:
            try:
                if self.rotation_input_active: self.rotation_angle = float(getattr(self, target_text)) % 360
                else: self.brush_thickness = max(1, int(getattr(self, target_text)))
            except (ValueError,TypeError): pass
            self.rotation_input_active = self.thickness_input_active = False
            setattr(self, target_text, "")
        elif event.key == pygame.K_BACKSPACE: setattr(self, target_text, getattr(self, target_text)[:-1])
        else:
            if not self.thickness_input_active or event.unicode.isdigit():
                 setattr(self, target_text, getattr(self, target_text) + event.unicode)
    
    def handle_mouse_events(self, event):
        pos = pygame.mouse.get_pos()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rotation_input_active and not self.ui_elements.get('rotation_input', pygame.Rect(0,0,0,0)).collidepoint((pos[0], pos[1] + self.panel_scroll_y)): self.rotation_input_active = False
            if self.thickness_input_active and not self.ui_elements.get('thickness_input', pygame.Rect(0,0,0,0)).collidepoint((pos[0], pos[1] + self.panel_scroll_y)): self.thickness_input_active = False
            
            if pos[0] < self.panel_width:
                grabber = self.ui_elements.get('scrollbar_grabber')
                if grabber and grabber.collidepoint(pos):
                    self.dragging_scrollbar = True
                    self.scrollbar_grabber_offset_y = pos[1] - grabber.y
                else:
                    scrolled_pos = (pos[0], pos[1] + self.panel_scroll_y)
                    self.handle_panel_click(scrolled_pos)
            else:
                if event.button == 1:
                    self.mouse_pressed = True; self.drag_start_pos = pos
                    world_pos = self.screen_to_world(pos)
                    if self.draw_mode not in [DrawMode.SELECT, DrawMode.CUT]:
                        self.action_in_progress = True
                        if self.draw_mode in [DrawMode.LINE, DrawMode.CIRCLE]: self.temp_points = [world_pos]
                        elif self.draw_mode == DrawMode.POLYGON: self.current_polygon.append(world_pos)
                        elif self.draw_mode == DrawMode.POINT:
                             self.shapes.append(Shape('point', [world_pos], self.current_draw_color, self.brush_thickness)); self.action_in_progress = False
                        elif self.draw_mode == DrawMode.FREEHAND: self.temp_points = [world_pos]
                elif event.button == 3:
                     if self.draw_mode == DrawMode.POLYGON and len(self.current_polygon) > 2:
                         self.shapes.append(Shape('polygon', self.current_polygon, self.current_draw_color, self.brush_thickness)); self.current_polygon = []; self.action_in_progress = False
                     else: self.panning = True; self.drag_start_pos = pos
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                world_pos = self.screen_to_world(pos)
                if self.action_in_progress:
                    if self.draw_mode == DrawMode.LINE: self.shapes.append(Shape('line', [self.temp_points[0], world_pos], self.current_draw_color, self.brush_thickness))
                    elif self.draw_mode == DrawMode.CIRCLE: self.shapes.append(Shape('circle', [self.temp_points[0], world_pos], self.current_draw_color, self.brush_thickness))
                    elif self.draw_mode == DrawMode.FREEHAND: self.shapes.append(Shape('freehand', self.temp_points, self.current_draw_color, self.brush_thickness))
                
                if self.drag_start_pos:
                    rect_screen = pygame.Rect(self.drag_start_pos, (pos[0] - self.drag_start_pos[0], pos[1] - self.drag_start_pos[1])); rect_screen.normalize()
                    p1_world, p2_world = self.screen_to_world(rect_screen.topleft), self.screen_to_world(rect_screen.bottomright)
                    rect_world = pygame.Rect(p1_world, (p2_world[0] - p1_world[0], p2_world[1] - p1_world[1]))
                    
                    if self.draw_mode == DrawMode.SELECT:
                        if np.linalg.norm(np.array(pos) - np.array(self.drag_start_pos)) < 5:
                            for s in reversed(self.shapes):
                               if any(pygame.Rect(s.points.min(axis=0), s.points.max(axis=0)-s.points.min(axis=0)).collidepoint(p) for p in [self.screen_to_world(pos)]): s.selected = not s.selected; break
                        else:
                            for s in self.shapes: s.selected = any(rect_world.collidepoint(p) for p in s.points)
                    
                    elif self.draw_mode == DrawMode.CUT and rect_screen.width > 2 and rect_screen.height > 2:
                        self.cut_shapes_with_rect(rect_world)

                self.mouse_pressed = False; self.action_in_progress = False; self.temp_points = []
            elif event.button == 3: self.panning = False
            self.dragging_scrollbar = False
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging_scrollbar:
                if self.panel_content_height > self.height:
                    grabber_height = max(25, self.height * (self.height / self.panel_content_height))
                    track_height = self.height - 10 - grabber_height
                    new_grabber_y = pos[1] - self.scrollbar_grabber_offset_y
                    scroll_percent = np.clip((new_grabber_y - 5) / track_height, 0, 1)
                    self.panel_scroll_y = scroll_percent * (self.panel_content_height - self.height)
            elif self.panning: self.pan_offset += np.array(pos) - np.array(self.drag_start_pos); self.drag_start_pos = pos
            elif self.mouse_pressed:
                 if self.draw_mode == DrawMode.FREEHAND: self.temp_points.append(self.screen_to_world(pos))
                 elif self.draw_mode == DrawMode.SELECT and self.transform_mode == TransformMode.TRANSLATE and any(s.selected for s in self.shapes):
                     delta = self.screen_to_world(pos) - self.screen_to_world(self.drag_start_pos)
                     for s in self.shapes:
                         if s.selected: s.points += delta
                     self.drag_start_pos = pos
        elif event.type == pygame.MOUSEWHEEL:
            if pos[0] > self.panel_width:
                zoom_center_world = self.screen_to_world(pos); zoom_delta = 1.1 if event.y > 0 else 1/1.1
                self.zoom_factor *= zoom_delta; self.pan_offset = pos - zoom_center_world * self.zoom_factor - np.array(self.draw_area.topleft)
            else:
                 if self.panel_content_height > self.height:
                    self.panel_scroll_y -= event.y * 30
                    self.panel_scroll_y = np.clip(self.panel_scroll_y, 0, self.panel_content_height - self.height)
                 elif self.transform_mode == TransformMode.SCALE: self.transform_factor = max(0.1, self.transform_factor + event.y * 0.1)
                 elif self.transform_mode == TransformMode.ROTATE: self.rotation_angle = (self.rotation_angle + event.y * 5) % 360
                 else: self.brush_thickness = max(1, self.brush_thickness + event.y)

    def handle_panel_click(self, scrolled_pos):
        color = self.color_wheel.get_color_at_pos(scrolled_pos)
        if color: self.current_draw_color = color
        for key, rect in self.ui_elements.items():
            if key != 'scrollbar_grabber' and rect.collidepoint(scrolled_pos):
                if isinstance(key, DrawMode): self.draw_mode = key
                elif isinstance(key, TransformMode): self.transform_mode = key
                elif isinstance(key, LineAlgorithm): self.line_algorithm = key
                elif key == 'thickness_inc': self.brush_thickness = min(50, self.brush_thickness + 1)
                elif key == 'thickness_dec': self.brush_thickness = max(1, self.brush_thickness - 1)
                elif key == 'thickness_input': self.thickness_input_active = True; self.thickness_input_text = ""
                elif key == 'rotation_input': self.rotation_input_active = True; self.rotation_input_text = ""
                elif key == 'factor_inc': self.transform_factor = min(3.0, self.transform_factor + 0.1)
                elif key == 'factor_dec': self.transform_factor = max(0.1, self.transform_factor - 0.1)
                elif key == 'zoom_in': self.zoom_factor = min(5.0, self.zoom_factor * 1.2)
                elif key == 'zoom_out': self.zoom_factor = max(0.2, self.zoom_factor / 1.2)
                elif key == 'zoom_reset': self.zoom_factor = 1.0; self.pan_offset = np.array([0.0, 0.0])
                break

    def handle_keyboard_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DELETE: self.shapes = [s for s in self.shapes if not s.selected]
            elif event.key == pygame.K_c: self.shapes.clear()
            elif event.key == pygame.K_ESCAPE:
                self.current_polygon, self.temp_points = [], []; self.action_in_progress = False
                for s in self.shapes: s.selected = False
            elif event.key == pygame.K_RETURN:
                selected_shapes = [s for s in self.shapes if s.selected]
                if not selected_shapes: return
                all_points = np.vstack([s.points for s in selected_shapes])
                centroid = np.mean(all_points, axis=0)
                matrix = self.get_transform_matrix(centroid)
                for s in selected_shapes: s.points = self.apply_matrix_to_points(s.points, matrix)

    def cut_shapes_with_rect(self, clip_rect_world):
        """Usa um retângulo para cortar todas as formas, removendo o que está dentro."""
        original_shapes = self.shapes[:]
        self.shapes = []
        for shape in original_shapes:
            if shape.type == 'point':
                if not clip_rect_world.collidepoint(shape.points[0]):
                    self.shapes.append(shape)
                continue

            # Para todas as outras formas, trate-as como uma coleção de arestas
            edges = []
            if shape.type == 'line':
                edges.append((shape.points[0], shape.points[1]))
            elif shape.type == 'polygon':
                for i in range(len(shape.points)):
                    edges.append((shape.points[i], shape.points[(i + 1) % len(shape.points)]))
            elif shape.type == 'freehand':
                for i in range(len(shape.points) - 1):
                    edges.append((shape.points[i], shape.points[i + 1]))
            elif shape.type == 'circle':
                center = shape.points[0]
                radius = np.linalg.norm(shape.points[1] - shape.points[0])
                # Aproxima o círculo com um polígono de 36 lados para o corte
                num_segments = 36
                circle_points = []
                for i in range(num_segments):
                    angle = 2 * math.pi * i / num_segments
                    circle_points.append(center + np.array([radius * math.cos(angle), radius * math.sin(angle)]))
                for i in range(num_segments):
                    edges.append((circle_points[i], circle_points[(i + 1) % num_segments]))

            if not edges:
                self.shapes.append(shape)
                continue

            is_cut = False
            new_edges = []
            for p1, p2 in edges:
                segments = self.split_line_with_rect(p1, p2, clip_rect_world)
                if len(segments) != 1 or not np.allclose(segments[0], [p1, p2]):
                    is_cut = True
                new_edges.extend(segments)

            if not is_cut:
                self.shapes.append(shape)
            else:
                # Se a forma foi cortada, ela é recriada como um conjunto de linhas
                for edge in new_edges:
                    self.shapes.append(Shape('line', edge, shape.color, shape.thickness))

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.draw_canvas()
            self.draw_ui()
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()

if __name__ == "__main__":
    app = PaintCG()
    app.run()


