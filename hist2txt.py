#!/usr/bin/env python

import array
import os
import sys
import time
from pdb import set_trace
from optparse import OptionParser
import math

inf = float('inf')
nan = float('nan')

def odg(num):
    if num == 0.:
        return 0.
    return int(
        math.log10(
            abs(num)
            )
        )

def prettyfloat(value, lenght):
    if value == inf or math.isnan(value):
        ret = value.__repr__().center(lenght)
    else:     
        odm = odg(value)
        accuracy = '0' if odm > 1 else \
           '1' if odm > -1 else \
           str(1-odm)
        ret = (('%.'+accuracy+'f') % value ).center(lenght)
        if len(ret) > lenght:
            ret = ('%.1e' % value ).center(lenght)
    return ret

def h1d_to_txt(histo, options):
    xbins = histo.GetNbinsX()
    size  = 9 if not options.compact else 5
    centers = ['uflow'.center(size)] if not options.range else []
    vals    = [prettyfloat(histo.GetBinContent(0), size)] if not options.range else []
    errs    = [prettyfloat(histo.GetBinError(0), size)] if not options.range else []
    x_range = eval(options.range) if options.range else None

    for i in xrange( 1, xbins+1 ):
        if x_range is not None:
            if not (x_range[0] <= histo.GetXaxis().GetBinCenter(i) <= x_range[1]):
                continue
        if options.binrange:
            centers.append( prettyfloat( histo.GetXaxis().GetBinLowEdge(i), size/2) + '-' + \
                            prettyfloat( histo.GetXaxis().GetBinLowEdge(i) + histo.GetXaxis().GetBinWidth(i), size/2) )
        elif options.labels:
            label = histo.GetXaxis().GetBinLabel(i)[:size]
            centers.append( label.center(size) )
        else:
            centers.append( prettyfloat( histo.GetXaxis().GetBinCenter(i), size) )
        vals.append( prettyfloat( histo.GetBinContent(i), size) )
        errs.append( prettyfloat( histo.GetBinError(i), size) )

    if x_range is None:
        centers.append( 'oflow'.center(size) )
        vals.append( prettyfloat( histo.GetBinContent(xbins+1), size) )
        errs.append( prettyfloat( histo.GetBinError(xbins+1), size) )

    firstline = '|'.join(vals)
    print firstline
    if options.stat:
        print '|'.join( '+/-'.center(size) for _ in vals)
        print '|'.join( errs )
    print '='*len(firstline)
    print '|'.join(centers)

#def h2d_to_txt(histo, options):
#    xbins = histo.GetNbinsX()
#    ybins = histo.GetNbinsY()
#    size  = 9
#    centers = ['uflow'.center(size)]
#    vals    = [prettyfloat(histo.GetBinContent(0), size)]
#    errs    = [prettyfloat(histo.GetBinError(0), size)]
#
#    for i in xrange( 1, xbins+1 ):
#        centers.append( prettyfloat( histo.GetXaxis().GetBinCenter(i), size) )
#        vals.append( prettyfloat( histo.GetBinContent(i), size) )
#        errs.append( prettyfloat( histo.GetBinError(i), size) )
#
#    centers.append( 'oflow'.center(size) )
#    vals.append( prettyfloat( histo.GetBinContent(xbins+1), size) )
#    errs.append( prettyfloat( histo.GetBinError(xbins+1), size) )
#
#    firstline = '|'.join(vals)
#    print firstline
#    if options.stat:
#        print '|'.join( '+/-'.center(size) for _ in vals)
#        print '|'.join( errs )
#    print '='*len(firstline)
#    print '|'.join(centers)
#

def rebin(histo, binning):
    if isinstance(binning, int):
        histo.Rebin(binning)
        return histo
    elif isinstance(binning, (list, tuple)):
        bin_array = array.array('d', binning)
        return histo.Rebin(len(binning)-1, str(time.time), bin_array)
    raise ValueError('Wrong binning value, only integers and lists/tuples are supported, got a %s' % type(binning))

def project(histo, axis):
    paxis = 'X'
    if axis.upper() == 'X':
        paxis = 'Y'

    nbins = getattr(histo, 'GetNbins%s' % paxis)()
    return getattr(histo, 'Projection%s' % axis.upper())(str(time.time()+1), 0, nbins+1)

__doc__ = 'prints a histogram to screen'
parser = OptionParser(description=__doc__)
parser.add_option('--show-errors', '-s', action='store_true', default = False,
                  help='show the statistical error', dest='stat')
parser.add_option('--bin-range', action='store_true', default = False,
                  help='', dest='binrange')
parser.add_option('--compact', action='store_true', default = False,
                  help='', dest='compact')
parser.add_option('--rebin', default = '', type=str,
                  help='rebins the histogram', dest='rebin')
parser.add_option('--project', default = '', type=str,
                  help='rebins the histogram', dest='project'
)
parser.add_option('--use-labels', dest='labels', action='store_true', default = False,
                  help='uses labels instead of bin center')
parser.add_option('--range', dest='range', type=str, default = '',
                  help='set printing range')
options, args = parser.parse_args()

import ROOT
fname = args[0]
path  = args[1]

tfile = ROOT.TFile.Open(fname)
histo = tfile.Get(path)

if options.project:
    histo = project(histo, options.project)

if options.rebin:
    histo = rebin(histo, eval(options.rebin))

h1d_to_txt(histo, options)
