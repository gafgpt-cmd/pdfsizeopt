"""Lossless predictor decoding delegated to the maintained qpdf engine."""

import pikepdf

DecodeError = pikepdf.PdfError


def unfilter(data, predictor, colors, bits, columns):
  with pikepdf.Pdf.new() as pdf:
    stream = pikepdf.Stream(
        pdf, data, Filter=pikepdf.Name.FlateDecode,
        DecodeParms=pikepdf.Dictionary(Predictor=predictor, Colors=colors,
                                      BitsPerComponent=bits, Columns=columns))
    return stream.read_bytes()
