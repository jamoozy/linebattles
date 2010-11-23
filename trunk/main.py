#!/usr/bin/env python
import sys
import math
import time
import random
random.seed(time.time())

#from OpenGL.GL import *
#from OpenGL.GLU import *

import pygame
from pygame.locals import *



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

  def collides(self, that):
    if isinstance(that, Ship):
      return self._build_rect().colliderect(that._build_rect())
    elif isinstance(that, Bullet):
      # Bullets vary greatly in how their collision detection
      # is meant to work.
      return that.collides(self)
    else:
      print 'Warning! Ship-%d collision detection??' % type(that)
      return False



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
    self.gun = Gun(screen, 0)

  def okay_to_fire(self):
    ticks = pygame.time.get_ticks()
    if self.last_fire_time + self.fire_delay <= ticks:
      self.last_fire_time = ticks
      return True
    return False

  def draw(self):
    if self.exploding:
      self.expl_prog += .5
      pygame.draw.circle(self.screen, (255,0,0), 
          (int(self.pos[0]),int(self.pos[1])), int(self.expl_prog))
    else:
      Ship.draw(self)

  def fire(self, traj):
    return self.okay_to_fire() and self.gun.fire(self.pos, traj) or ()

  def explode(self):
    self.exploding = True

  @staticmethod
  def spawn_at(screen, x, y):
    ship = Player(screen)
    ship.pos = [x,y]
    return ship



##########################################################################
#                               Bullets                                  #
##########################################################################

class Bullet(object):
  def __init__(self, screen, pos, traj):
    self.screen = screen
    self.pos = list(pos)
    self.traj = traj
    self.speed = 4.
    self.length = 10
    self.color = 255,0,0

  def collides(self, that):
    if not isinstance(that, Ship):
      print 'Warning!  Bullet-non-Ship collision check???'
      return False
    return that._build_rect().collidepoint(self.pos)

  def _calc_shift(self):
    return [ self.speed * math.cos(self.traj),
             self.speed * math.sin(self.traj) ]

  def _calc_tail_pos(self):
    return [ self.pos[0] - self.length * math.cos(self.traj),
             self.pos[1] - self.length * math.sin(self.traj) ]

  def draw(self):
    pygame.draw.line(self.screen, self.color,
                     self.pos, self._calc_tail_pos(), 2)

  def tick(self):
    self.move_forward()

  def move_forward(self):
    shift = self._calc_shift()
    self.pos[0] += shift[0]
    self.pos[1] += shift[1]

class Gun(object):
  def __init__(self, screen, num_bullets = 1):
    self.screen = screen
    self.power = num_bullets

  def fire(self, pos, traj):
    bullets = []
    for i in xrange(-self.power, self.power + 1, 2):
      bullets.append(Bullet(self.screen, pos, traj + i / 100.))
    return bullets



##########################################################################
#                               Baddies                                  #
##########################################################################

class Baddie(Ship):
  def __init__(self, screen, color, pos, traj, size, geom):
    Ship.__init__(self, screen, color, geom, size = size)
    self.pos = list(pos)
    self.traj = traj
    self.speed = .5

  def tick(self):
    '''Perform one frame of action.'''
    print 'Warning: Baddie.tick() called'

class Wiggler(Baddie):
  def __init__(self, screen, pos, traj):
    Baddie.__init__(self, screen, (0,255,0), pos, traj, 5,
            ((1,1), (1,-1), (-1,-1), (-1, 1)))

  def tick(self):
    '''Perform one frame of action.'''
    self.traj += random.randrange(-100,100,1) / 1000.
    while self.traj > 2 * math.pi: self.traj -= 2 * math.pi
    while self.traj < 0: self.traj += 2 * math.pi
    self.move_forward(self.speed)

class Homer(Baddie):
  def __init__(self, screen, pos, traj):
    Baddie.__init__(self, screen, (255,0,255), pos, traj, 5,
            ((2,0), (0,-1), (-2,0), (0,1)))
    self.speed = .4
    self.dt = .01  # max change in traj

  def tick(self):
    '''Perform one frame of action.'''
    dx = Main.get_main().player.pos[0] - self.pos[0]
    dy = Main.get_main().player.pos[1] - self.pos[1]
    self.traj = math.atan2(dy, dx)
    self.move_forward(self.speed)



class SpawnPoint(object):
  def __init__(self, screen, size, x, y, baddies_array):
    self.screen = screen
    self.pos = [x,y]
    self.baddies = baddies_array
    self.traj = math.atan2(size[0] / 2 - y, size[1] / 2 - x)
    self.queue = []

  def spawn(self, baddie_type = Wiggler):
    self.baddies.append(baddie_type(self.screen, self.pos, self.traj))

  def queue_spawn(self, baddie_type):
    self.queue.append(baddie_type)

  def tick(self):
    if len(self.queue) > 0 and random.randrange(100) < 20:
      self.spawn(self.queue[0])
      del self.queue[0]

  def draw(self):
    pass

  def clear(self):
    self.queue = []



class Level(object):
  def __init__(self, screen, size, spawn_point_array, greeting, progression):
    '''Creates a level.
    screen: SDL surface to draw to
    spawn_point_array: the spawn points
    greeting: the string to display when the level starts
    progression: The progression of the level.  Expected is a list of
                 4-tuples, where each tuple is:
                   1: pause time before wave start
                   2: index of spawn point to spawn at.
                   3: type of baddie to spawn
                   4: number of baddies to spawn'''
    self.screen = screen
    self.spawns = spawn_point_array

    self.font = pygame.font.SysFont("courier", 30, bold = True)
    self.greeting = greeting
    w,h = self.font.size(self.greeting)
    self.greeting_pos = (size[0] - w) / 2, (size[1] - h) / 2

    self.progression = progression
    self.prog_i = 0

  def start(self):
    self.prog_i = 0
    self.start_time = pygame.time.get_ticks()

  def _p(self):
    if self.prog_i < len(self.progression):
      return self.progression[self.prog_i]
    else:
      return (9e9999,-1,None,0)

  def tick(self):
    # Check/spawn queue
    if self.prog_i < len(self.progression):
      while self._p()[0] <= pygame.time.get_ticks() - self.start_time:
        for i in xrange(self._p()[3]):
          self.spawns[self._p()[1]].queue_spawn(self._p()[2])
        self.prog_i += 1

  def jump_to_next_wave(self):
    if self.prog_i != 0 and self.prog_i < len(self.progression):
      self.start_time = pygame.time.get_ticks() - self._p()[0]
    self.tick()

  def draw(self):
    if self.prog_i == 0:
      self.screen.blit(self.font.render(self.greeting, False,
              (255,255,255)), self.greeting_pos)

  def done(self):
    return self.prog_i >= len(self.progression)


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



class CollisionSpace(object):
  BINSIZE = 50
  BUFSIZE = .1

  def __init__(self, size, player):
    self.size = size
    self.player = player
    self.cols = size[0] / self.BINSIZE
    self.rows = size[1] / self.BINSIZE
    self.baddies = []
    self.bullets = []

  def tick(self):
    self.bad_bins = [[[]] * self.cols] * self.rows
    self.bul_bins = [[[]] * self.cols] * self.rows

    for b in self.baddies:
      b.tick()
      self._insert_baddie(b)
    for b in self.bullets:
      b.tick()
      self._insert_bullet(b)

    for i in xrange(self.cols):
      for j in xrange(self.rows):
        self._check_bin(self.bul_bins[i][j])

  def _get_bins_idxs(self, obj):
    bin_i = self.size[0] / obj.pos[0]
    bin_j = self.size[1] / obj.pos[1]
    i_pos = self.size[0] / float(obj.pos[0]) - bin_i
    j_pos = self.size[1] / float(obj.pos[1]) - bin_j

    l_bin = r_bin = False
    bins = [(bin_i, bin_j)]
    if bin_i > 0:
      if i_pos < self.BUFSIZE:
        l_bin = True
        bins.append((bin_i-1, bin_j))
    elif bin_i < len(self.cols) - 1:
      if i_pos > self.BINSIZE - self.BUFSIZE:
        r_bin = True
        bins.append((bin_i+1, bin_j))

    if bin_j > 0:
      if j_pos < self.BUFSIZE:
        bins.append((bin_i, bin_j-1))
        if l_bin:
          bins.append((bin_i-1, bin_j-1))
        elif r_bin:
          bins.append((bin_i+1, bin_j-1))
    elif bin_j < len(self.rows) - 1:
      if j_pos > self.BINSIZE - self.BUFSIZE:
        bins.append((bin_i, bin_j))
        if l_bin:
          bins.append((bin_i-1, bin_j+1))
        elif r_bin:
          bins.append((bin_i+1, bin_j+1))

    return bins
    
  def _insert_baddie(self, b):
    for idx in self._get_bins_idxs(b):
      self.bad_bins[idx[0],idx[1]].append(b)
    
  def _insert_bullet(self, b):
    for idx in self._get_bins_idxs(b):
      self.bul_bins[idx[0],idx[1]].append(b)

  def _remove_bullet(self, b, idxs = None):
    if idxs is None:
      idxs = self._get_bins_idxs(b)
    for i,j in idxs:
      self.bul_bins[i][j].remove(b)
    self.bullets.remove(b)

  def _remove_baddie(self, b, idxs = None):
    if idxs is None:
      idxs = self._get_bins_idxs(b)
    for i,j in idxs:
      self.bad_bins[i][j].remove(b)
    self.baddies.remove(b)

  def _check_bin(self, bul_bin):
    for i in xrange(len(bul_bin)-1,-1,-1):
      idxs = self._get_bins_idxs(bul_bin[i])
      for i,j in idxs:
        pass#self.bad_bins[
      bins = self._get_bins_for_baddie(self.bad_bins[i][j][k])
      for b in bins:
        for l in xrange(len(b)-1,-1,-1):
          if b[l].collides(self.bad_bins[i][j][k]):
            print 'hit and remove'
            del self.bad_bins[i][j][k]
            del b[l]

  def add(self, obj):
    if isinstance(obj, Bullet):
      self.bullets.append(obj)
    elif isinstance(obj, Baddie):
      self.baddies.append(obj)
    else:
      print 'Unrecognized type in CollisionSpace.add():', type(obj)



class Main(object):
  def __init__(self):
    pygame.init()
    self.size = self.width, self.height = 800, 600
    self.screen = pygame.display.set_mode(self.size, HWSURFACE | DOUBLEBUF)

    self.player = Player.spawn_at(self.screen, self.width/2, self.height/2)
    self.speed = 2
    self.black = (0,0,0)

    self.fps_timer = pygame.time.Clock()

    # fonts
    self.score_font = pygame.font.SysFont('courier', 25, bold = True)
    self.debug_font = pygame.font.SysFont('arial', 8)
    self.gameover_font = pygame.font.SysFont('arial', 18, bold = True)
    self.gameover_pos = self.gameover_font.size('GAME OVER')
    self.gameover_pos = (self.width - self.gameover_pos[0]) / 2, \
                        (self.height - self.gameover_pos[1]) / 2
    self.winner_font = pygame.font.SysFont('arial', 18, bold = True)
    self.winner_pos = self.winner_font.size('WINNER')
    self.winner_pos = (self.width - self.winner_pos[0]) / 2, \
                      (self.height - self.winner_pos[1]) / 2

    self.user_input = Input()
    self.bullets = []
    self.baddies = []
    dw, dh = .1 * self.width, .1 * self.height
    self.spawn_points = [
        SpawnPoint(self.screen, self.size,
                             dw,               dh, self.baddies),
        SpawnPoint(self.screen, self.size,
                             dw, self.height - dh, self.baddies),
        SpawnPoint(self.screen, self.size,
                self.width - dw,               dh, self.baddies),
        SpawnPoint(self.screen, self.size,
                self.width - dw, self.height - dh, self.baddies) ]
    self.score = 0
    self.winner = False

    self.lev_i = 0
    self.levels = [ Level(self.screen, self.size, self.spawn_points,
                          "Level 1", [ (2e3, 0, Wiggler, 20),
                                       (2e3, 1, Wiggler, 20),
                                       (2e3, 2, Homer, 20),
                                       (2e3, 3, Wiggler, 20) ]),
                    Level(self.screen, self.size, self.spawn_points,
                          "Level 2", [ (2000, 0, Wiggler, 200),
                                       (2000, 1, Wiggler, 200),
                                       (2000, 2, Wiggler, 200),
                                       (2000, 3, Wiggler, 200) ]),
                    Level(self.screen, self.size, self.spawn_points,
                          "Level 3", [ (2000, 0, Wiggler, 2000),
                                       (2000, 1, Wiggler, 2000),
                                       (2000, 2, Wiggler, 2000),
                                       (2000, 3, Wiggler, 2000) ]) ]


  def run(self):

    ######################################################################
    #                              Main Loop                             #
    ######################################################################

    self.levels[self.lev_i].start()

    while True:
      self.fps_timer.tick(60)


      ####################################################################
      #                            User Input                            #
      ####################################################################

      # Quitting and special keys.
      for event in pygame.event.get([pygame.QUIT, pygame.KEYUP]):
        if event.type == pygame.QUIT:
          sys.exit()
        if event.type == pygame.KEYUP:
          if (event.key == pygame.K_q or event.key == pygame.K_w) and \
             (event.mod == pygame.K_RCTRL or event.mod == pygame.K_LCTRL):
            sys.exit()
          elif event.key == pygame.K_F7:
            self.spawn_points[random.randrange(len(self.spawn_points))].spawn()
          elif event.key == pygame.K_RIGHTBRACKET:
            self.player.gun.power += 1
          elif event.key == pygame.K_LEFTBRACKET:
            if self.player.gun.power > 0:
              self.player.gun.power -= 1
          elif event.key == pygame.K_F6:
            print 'stats:'
            print '  Num Baddies:', len(self.baddies)
            print '  Num Bullets:', len(self.bullets)
      pygame.event.clear()

      # Movement
      if self.player.exploding:
        # explode and restart
        if self.player.expl_prog >= 30:
          for s in self.spawn_points: s.clear()
          del self.player
          self.player = Player.spawn_at(self.screen, self.width / 2, self.height / 2)
          self.empty_lists()
          self.score = 0
          self.levels[self.lev_i].start()
      else:
        js_dx = self.user_input.get_mx()
        js_dy = self.user_input.get_my()
        self.player.traj = math.atan2(js_dy, js_dx)
        if abs(js_dx) > .1 or abs(js_dy) > .1:
          amt = math.sqrt(js_dx * js_dx + js_dy * js_dy)
          if amt > 1:
            amt = 1.
          elif amt < -1:
            amt = -1.
          self.player.move_forward(self.speed * amt)

        # Fire
        js_fx = self.user_input.get_fx()
        js_fy = self.user_input.get_fy()
        if abs(js_fx) > .1 or abs(js_fy) > .1:
          for b in self.player.fire(math.atan2(js_fy, js_fx)):
            self.bullets.append(b)


        ##################################################################
        #                      Collision Detection                       #
        ##################################################################

        while self.player._build_rect().left <= 0:
          self.player.move(1,0)
        while self.player._build_rect().right >= self.width:
          self.player.move(-1,0)
        while self.player._build_rect().top <= 0:
          self.player.move(0,1)
        while self.player._build_rect().bottom >= self.height:
          self.player.move(0,-1)


      ####################################################################
      #                        Level Progression                         #
      ####################################################################

      if self.lev_i < len(self.levels) and self.no_more_baddies():
        if self.levels[self.lev_i].done():
          self.lev_i += 1
          if self.lev_i < len(self.levels):
            self.levels[self.lev_i].start()
          else:
            winner = True
        else:
          self.levels[self.lev_i].jump_to_next_wave()
      else:
        self.levels[self.lev_i].tick()

      #self.space.tick()
      for b in self.baddies: b.tick()
      for b in self.bullets: b.tick()
      for s in self.spawn_points: s.tick()
      


      ####################################################################
      #                         Drawing Process                          #
      ####################################################################

      self.screen.fill(self.black)

      for s in self.spawn_points: s.draw()

      if self.lev_i < len(self.levels):
        self.levels[self.lev_i].draw()

      # draw the bullets or delete them if they've gone off screen
      # --> reverse search, because we're deleting elements
      for i in xrange(len(self.bullets)-1,-1,-1):
        if self.bullets[i].pos[0] <= 0 or self.bullets[i].pos[0] >= self.width or \
           self.bullets[i].pos[1] <= 0 or self.bullets[i].pos[1] >= self.height:
          del self.bullets[i]
        else:
          self.bullets[i].draw()

      # draw the baddies or delete baddie/bullet on collision
      for i in xrange(len(self.baddies)-1,-1,-1):
        remove_me = False

        for j in xrange(len(self.bullets)):
          if self.bullets[j].collides(self.baddies[i]):
            remove_me = True
            del self.bullets[j]
            self.score += 100
            break

        if remove_me:
          del self.baddies[i]
        else:
          rect = self.baddies[i]._build_rect()
          if rect.left <= 0 or rect.right >= self.width:
            self.baddies[i].traj = math.pi - self.baddies[i].traj
            while self.baddies[i]._build_rect().left <= 0:
              self.baddies[i].move(1,0)
            while self.baddies[i]._build_rect().right >= self.width:
              self.baddies[i].move(-1,0)

          if rect.top <= 0 or rect.bottom >= self.height:
            self.baddies[i].traj = -self.baddies[i].traj
            while self.baddies[i]._build_rect().top <= 0:
              self.baddies[i].move(0,1)
            while self.baddies[i]._build_rect().bottom >= self.height:
              self.baddies[i].move(0,-1)

          self.baddies[i].draw()
          if not self.player.exploding:
            if rect.colliderect(self.player._build_rect()):
              self.player.explode()

      
      if self.winner:
        self.screen.blit(winner_font.render("WINNER", False,
          (255,255,255)), self.winner_pos)
      if self.player.exploding:
        self.screen.blit(self.gameover_font.render("GAME OVER", False,
          (255,255,255)), self.gameover_pos)
      self.screen.blit(self.score_font.render('%d' % self.score, False,
          (255,255,255)), (10,10))

      self.player.draw()
      pygame.display.flip()

  def spawn_points_empty(self):
    for sp in self.spawn_points:
      if len(sp.queue) != 0:
        return False
    return True

  def empty_list(self, l):
    while 0 < len(l): del l[0]

  def empty_lists(self):
    self.empty_list(self.bullets)
    self.empty_list(self.baddies)

  def no_more_baddies(self):
    return self.spawn_points_empty() and len(self.baddies) <= 0

  MAIN_OBJECT = None
  @staticmethod
  def get_main():
    if Main.MAIN_OBJECT is None:
      Main.MAIN_OBJECT = Main()
    return Main.MAIN_OBJECT


if __name__ == '__main__':
  Main.get_main().run()
