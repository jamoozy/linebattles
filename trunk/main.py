#!/usr/bin/env python
import sys
import math
import time
import random
random.seed(time.time())
import pygame

class Ship(object):
  '''This class is used for drawing, mainly.  Just pass it some points and
  things, and it'll handle the rest!'''
  def __init__(self, screen, color, points, pos = [0,0], traj = 0, size = 10):
    '''Create this!
    screen: The screen to draw on
    color: The color to draw
    points: Points consisting of the line-art
    pos: Initial position of the ship
    traj: Initial trajectory (0 radians is to the left, .5pi is down)
    size: Size of the ship.'''

    self.screen = screen
    self.color = color
    self.ps = points
    self.pos = list(pos)
    self.traj = traj
    self.size = size

    # rect ensures the bbox for this is calculated at most once per tick
    self.rect = None   # i.e., not up-to-date

  def move(self, dx, dy):
    self.rect = None
    self.pos[0] += dx
    self.pos[1] += dy

  def move_forward(self, speed):
    self.rect = None
    self.pos[0] += math.cos(self.traj) * speed
    self.pos[1] += math.sin(self.traj) * speed

  def rotate(self, dt):
    self.rect = None
    self.traj += dt
    while self.traj > 2 * math.pi:
      self.traj -= 2 * math.pi
    while self.traj < 0:
      self.traj += 2 * math.pi

  def _calc_global_ps(self):
    st = math.sin(self.traj) * self.size
    ct = math.cos(self.traj) * self.size
    return map(lambda p: [self.pos[0] + p[0] * ct - p[1] * st,
                          self.pos[1] + p[1] * ct + p[0] * st],
               self.ps)

  def _build_rect(self):
    if self.rect is None:
      ps = self._calc_global_ps()
      self.rect = pygame.Rect(ps[0],(0,0))
      for i in xrange(1,len(ps)):
        self.rect.union_ip(pygame.Rect(ps[i], (0,0)))
    return self.rect

  def center(self):
    return self._build_rect().center

  def draw(self):
    pygame.draw.lines(self.screen, self.color, True, self._calc_global_ps())



class Bullet(object):
  def __init__(self, screen, pos, traj):
    self.screen = screen
    self.pos = list(pos)
    self.traj = traj
    self.speed = 4.
    self.length = 10
    self.color = 255,0,0

  def _calc_shift(self):
    return [ self.speed * math.cos(self.traj),
             self.speed * math.sin(self.traj) ]

  def _calc_end_pos(self):
    return [ self.pos[0] - self.length * math.cos(self.traj),
             self.pos[1] - self.length * math.sin(self.traj) ]

  def draw(self):
    pygame.draw.line(self.screen, self.color,
                     self.pos, self._calc_end_pos(), 2)

  def move_forward(self):
    shift = self._calc_shift()
    self.pos[0] += shift[0]
    self.pos[1] += shift[1]



class Player(Ship):
  '''This should be unique in that it's the only ship that can also fire guns
  and stuff.'''
  def __init__(self, screen):
    Ship.__init__(self, screen, (200, 200, 255),
                  [ [ 0, -1], [ 2, -1], [ 0, -2], [-2, -1],
                    [ 0, -1], [ 0,  1], [ 2,  1], [ 0,  2],
                    [-2,  1], [ 0,  1], [-2, -1], [-2,  1] ],
                  size = 5)
    self.last_fire_time = 0
    self.fire_delay = 100 # ms
    self.exploding = False
    self.expl_prog = 0

  def okay_to_fire(self):
    ticks = pygame.time.get_ticks()
    if self.last_fire_time + self.fire_delay <= ticks:
      self.last_fire_time = ticks
      return True
    return False

  def draw(self):
    if self.exploding:
      self.expl_prog += .5
      pygame.draw.circle(self.screen, (255,0,0), self.pos, self.expl_prog)
    else:
      Ship.draw(self)

  def fire(self, traj):
    if self.okay_to_fire():
      return Bullet(self.screen, self.pos, traj)
    else:
      return None

  def explode(self):
    self.exploding = True

  @staticmethod
  def spawn_at(screen, x, y):
    ship = Player(screen)
    ship.pos = [x,y]
    return ship



class Baddie(Ship):
  def __init__(self, screen, pos, traj):
    Ship.__init__(self, screen, (0, 255, 0),
                  [ [ 1, 1], [ 1, -1], [-1, -1], [-1,  1] ], size = 5) 
    self.pos = list(pos)
    self.traj = traj
    self.speed = 1

  def tick(self):
    '''Perform one frame of action.'''
    self.traj += random.randrange(-100,100,1) / 1000.
    while self.traj > 2 * math.pi: self.traj -= 2 * math.pi
    while self.traj < 0: self.traj += 2 * math.pi
    self.move_forward(self.speed)




class SpawnPoint(object):
  def __init__(self, screen, x, y, baddies_array):
    global width,height
    self.screen = screen
    self.pos = [x,y]
    self.baddies = baddies_array
    self.traj = math.atan2(height / 2 - y, width / 2 - x)

  def spawn(self):
    self.baddies.append(Baddie(self.screen, self.pos, self.traj))



class Input(object):
  def __init__(self):
    if pygame.joystick.get_count() > 0:
      self.js = pygame.joystick.Joystick(0)
      self.js.init()
      print 'using %d axes' % self.js.get_numaxes()
    else:
      self.js = None

  def get_mx(self):
    '''Gets movement in the X direction (in [-1,1] for [left,right]).'''
    if self.js is None:
      keys = pygame.key.get_pressed()
      if keys[pygame.K_f]:
        return 1.
      elif keys[pygame.K_s]:
        return -1.
      else:
        return .0
    else:
      return self.js.get_axis(0)

  def get_my(self):
    '''Gets movement in the Y direction (in [-1,1] for [top,bottom]).'''
    if self.js is None:
      keys = pygame.key.get_pressed()
      if keys[pygame.K_d]:
        return 1.
      elif keys[pygame.K_e]:
        return -1.
      else:
        return .0
    else:
      return self.js.get_axis(1)

  def get_fx(self):
    '''Gets fire direction in X (in [-1,1] for [left,right]).'''
    if self.js is None:
      keys = pygame.key.get_pressed()
      if keys[pygame.K_l]:
        return 1.
      elif keys[pygame.K_j]:
        return -1.
      else:
        return .0
    else:
      return self.js.get_axis(2)

  def get_fy(self):
    '''Gets fire direction in Y (in [-1,1] for [top,bottom]).'''
    if self.js is None:
      keys = pygame.key.get_pressed()
      if keys[pygame.K_k]:
        return 1.
      elif keys[pygame.K_i]:
        return -1.
      else:
        return .0
    else:
      return self.js.get_axis(3)



def empty(l):
  ind = range(len(l))
  ind.reverse()
  for i in ind: del l[i]

size = width,height = 480,320
def run():
  pygame.init()
  screen = pygame.display.set_mode(size)

  ship = Player.spawn_at(screen, width/2, height/2)
  speed = 2
  black = (0,0,0)

  fps_timer = pygame.time.Clock()

  # fonts
  score_font = pygame.font.SysFont('courier', 25, bold = True)
  debug_font = pygame.font.SysFont('arial', 8)
  gameover_font = pygame.font.SysFont('arial', 18, bold = True)
  gameover_pos = gameover_font.size('GAME OVER')
  gameover_pos = (width - gameover_pos[0]) / 2, \
                 (height - gameover_pos[1]) / 2
  winner_font = pygame.font.SysFont('arial', 18, bold = True)
  winner_pos = winner_font.size('WINNER')
  winner_pos = (width - winner_pos[0]) / 2, \
               (height - winner_pos[1]) / 2

  user_input = Input()
  bullets = []
  baddies = []
  dw, dh = .1 * width, .1 * height
  spawn_points = [ SpawnPoint(screen,         dw,          dh, baddies),
                   SpawnPoint(screen,         dw, height - dh, baddies),
                   SpawnPoint(screen, width - dw,          dh, baddies),
                   SpawnPoint(screen, width - dw, height - dh, baddies) ]
  score = 0
  max_ships = 100
  num_ships_spawned = 0
  winner = False


  ######################################################################
  #                              Main Loop                             #
  ######################################################################

  while True:
    fps_timer.tick(60)


    ####################################################################
    #                            User Input                            #
    ####################################################################

    # Quitting and special keys.
    for event in pygame.event.get([pygame.QUIT, pygame.KEYUP]):
      if event.type == pygame.QUIT:
        sys.exit()
      if event.type == pygame.KEYUP and \
        (event.key == pygame.K_q or event.key == pygame.K_w) and \
        (event.mod == pygame.K_RCTRL or event.mod == pygame.K_LCTRL):
        sys.exit()
      if event.type == pygame.KEYUP and event.key == pygame.K_F7:
        spawn_points[random.randrange(len(spawn_points))].spawn()
      if event.type == pygame.KEYUP and event.key == pygame.K_F6:
        print 'stats:'
        print '  Num Baddies:', len(baddies)
        print '  Num Bullets:', len(bullets)
    pygame.event.clear()

    # Movement
    if ship.exploding:
      if ship.expl_prog >= 30:
        del ship
        ship = Player.spawn_at(screen, width/2, height/2)
        empty(bullets)
        empty(baddies)
        score = 0
        num_ships_spawned = 0
    else:
      js_dx = user_input.get_mx()
      js_dy = user_input.get_my()
      ship.traj = math.atan2(js_dy, js_dx)
      if abs(js_dx) > .1 or abs(js_dy) > .1:
        amt = math.sqrt(js_dx * js_dx + js_dy * js_dy)
        if amt > 1:
          amt = 1.
        elif amt < -1:
          amt = -1.
        ship.move_forward(speed * amt)

      # Fire
      js_fx = user_input.get_fx()
      js_fy = user_input.get_fy()
      if abs(js_fx) > .1 or abs(js_fy) > .1:
        bullet = ship.fire(math.atan2(js_fy, js_fx))
        if bullet is not None:
          bullets.append(bullet)


      ##################################################################
      #                      Collision Detection                       #
      ##################################################################

      while ship._build_rect().left <= 0:
        ship.move(1,0)
      while ship._build_rect().right >= width:
        ship.move(-1,0)
      while ship._build_rect().top <= 0:
        ship.move(0,1)
      while ship._build_rect().bottom >= height:
          ship.move(0,-1)


      if num_ships_spawned < max_ships:
        if random.randrange(100) < 5:
          for s in spawn_points:
            s.spawn()
            num_ships_spawned += 1
      elif len(baddies) <= 0:
        winner = True

    ####################################################################
    #                         Drawing Process                          #
    ####################################################################

    screen.fill(black)

    # draw the bullets or delete them if they've gone off screen
    indecies = range(len(bullets))
    indecies.reverse()
    for i in indecies:  # reverse search, because we're deleting elements
      bullets[i].move_forward()
      if bullets[i].pos[0] <= 0 or bullets[i].pos[0] >= width or \
         bullets[i].pos[1] <= 0 or bullets[i].pos[1] >= height:
        del bullets[i]
      else:
        bullets[i].draw()

    # draw the baddies or delete baddie/bullet on collision
    indecies = range(len(baddies))
    indecies.reverse()
    for i in indecies:
      baddies[i].tick()
      rect = baddies[i]._build_rect()
      remove_me = False

      for j in xrange(len(bullets)):
        if rect.collidepoint(bullets[j].pos):
          remove_me = True
          del bullets[j]
          score += 100
          break

      if remove_me:
        del baddies[i]
      else:
        if rect.left <= 0 or rect.right >= width:
          baddies[i].traj = math.pi - baddies[i].traj
          while baddies[i]._build_rect().left <= 0:
            baddies[i].move(1,0)
          while baddies[i]._build_rect().right >= width:
            baddies[i].move(-1,0)

        if rect.top <= 0 or rect.bottom >= height:
          baddies[i].traj = -baddies[i].traj
          while baddies[i]._build_rect().top <= 0:
            baddies[i].move(0,1)
          while baddies[i]._build_rect().bottom >= height:
            baddies[i].move(0,-1)

        baddies[i].draw()
        if not ship.exploding:
          if rect.colliderect(ship._build_rect()):
            ship.explode()

    
    if winner:
      screen.blit(winner_font.render("WINNER", False,
        (255,255,255)), winner_pos)
    if ship.exploding:
      screen.blit(gameover_font.render("GAME OVER", False,
        (255,255,255)), gameover_pos)
    screen.blit(score_font.render('%d' % score, False,
        (255,255,255)), (20,20))

    ship.draw()
    pygame.display.flip()

if __name__ == '__main__':
  run()
