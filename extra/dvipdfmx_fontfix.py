#!/usr/bin/env python3
# by pts@fazekas.hu at Tue Jul 21 16:14:10 CEST 2009

import re
import sys
import os
import subprocess


def main(argv):
  map_list = []

  cfg_kname = subprocess.check_output(
      ['kpsewhich', '--progname=dvipdfmx', 'dvipdfmx.cfg'],
      text=True, encoding='utf-8').rstrip('\n')
  for cfg_line in open(cfg_kname, encoding='utf-8'):
    cfg_items = cfg_line.strip().split(None, 1)
    if len(cfg_items) == 2 and cfg_items[0] == 'f':
      map_list.append(cfg_items[1])

  i = 1
  while i < len(argv):
    if argv[i] == '-f' and i < len(argv) - 1:
      map_list.append(argv[i + 1])
      i += 2
    elif argv[i].startswith('-f'):
      map_list.append(argv[i][2:])
      i += 1
    else:
      break

  f = open('dvipdfmx_base.map', 'w', encoding='utf-8')

  for map_name in map_list:
    map_kname = subprocess.check_output(
        ['kpsewhich', map_name], text=True, encoding='utf-8').rstrip('\n')
    assert map_kname, 'font map not found: %s' % map_name
 
    for map_line in open(map_kname, encoding='utf-8'):
      # A to-be-reencoded base font. Example:
      # ptmr8r Times-Roman "TeXBase1Encoding ReEncodeFont" <8r.enc
      match = re.match(r'\s*([^%\s]\S*)\s+(\S+)\s+(?:\d+\s+)?"([^"]*)"\s+'
                       r'<(\S+)[.]enc\s*\Z', map_line)
      if match:
        #print map_line,
        tex_font_name = match.group(1)
        ps_font_name = match.group(2)
        ps_instructions = ' %s ' % re.sub(r'\s+', ' ', match.group(3).strip())
        enc_file_name = match.group(4)
        dvipdfm_instructions = []
        # TODO(pts): Obey the order
        match = re.match(r' (\S+) SlantFont ', ps_instructions)
        if match:
          dvipdfm_instructions.append(' -s %s' % match.group(1))
        match = re.match(r' (\S+) ExtendFont ', ps_instructions)
        if match:
          dvipdfm_instructions.append(' -e %s' % match.group(1))
        f.write('%s %s %s%s\n' %
                (tex_font_name, enc_file_name, ps_font_name,
                 ' '.join(dvipdfm_instructions)))

  f.close()
  args = ['dvipdfmx', '-f', 'dvipdfmx_base.map'] + argv[1:]
  sys.stdout.flush()
  sys.stderr.flush()
  os.execlp(args[0], *args)

if __name__ == '__main__':
  sys.exit(main(sys.argv) or 0)
