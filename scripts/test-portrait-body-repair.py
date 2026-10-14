import copy
import unittest
import numpy as np
from PIL import Image,ImageDraw
from portrait_body_repair import make_masks,neutral_reference,repair_graph


def rectangle(box):
    im=Image.new('L',(128,160));ImageDraw.Draw(im).rectangle(box,fill=255);return im


class BodyRepairTests(unittest.TestCase):
    def test_entire_animal_editable_and_fur_removed_but_costume_retained(self):
        animal=rectangle((30,20,95,145));clothes=rectangle((35,55,90,100))
        mask,erase,_=make_masks(animal,animal,clothes,animal.size,grow=4,feather=2)
        self.assertEqual(mask.getpixel((40,140)),255)
        self.assertEqual(mask.getpixel((60,30)),255)
        self.assertEqual(mask.getpixel((0,0)),0)
        design=neutral_reference(Image.new('RGB',animal.size,'red'),erase)
        self.assertEqual(design.getpixel((60,130)),(127,127,127))
        self.assertEqual(design.getpixel((60,75)),(255,0,0))

    def test_invalid_segmentation_does_not_silently_generate(self):
        good=rectangle((30,20,95,145));clothes=rectangle((35,55,90,100))
        for bad in (Image.new('L',good.size,0),Image.new('L',good.size,255)):
            with self.assertRaises(ValueError):make_masks(bad,good,clothes,good.size)
        with self.assertRaises(ValueError):make_masks(good,good,Image.new('L',good.size,0),good.size)

    def test_exposed_fur_and_separate_clothes_are_combined_for_body_repair(self):
        fur=rectangle((45,15,80,45));ImageDraw.Draw(fur).rectangle((45,135,80,150),fill=255)
        clothes=rectangle((35,50,90,130))
        mask,erase,_=make_masks(fur,fur,clothes,fur.size,grow=4,feather=2,subject_clothes=clothes)
        self.assertEqual(mask.getpixel((60,90)),255)
        self.assertEqual(erase.getpixel((60,90)),0)
        self.assertEqual(erase.getpixel((60,140)),255)

    def test_bare_animal_requires_explicit_optional_clothing(self):
        animal=rectangle((30,20,95,145));empty=Image.new('L',animal.size,0)
        with self.assertRaises(ValueError):make_masks(animal,animal,empty,animal.size)
        mask,erase,_=make_masks(animal,animal,empty,animal.size,require_clothing=False)
        self.assertEqual(mask.getpixel((60,80)),255);self.assertEqual(erase.getpixel((60,80)),255)

    def test_graph_rebuilds_mask_and_preserves_background_without_pasting_input(self):
        base={key:{'inputs':{}} for key in ('76','detailimage','81','92:105','92:103','9','92:113')}
        before=copy.deepcopy(base)
        g=repair_graph(base,original='source.png',face='face.png',design='design.png',baseline='before.png',mask='mask.png',prefix='repair',identity='Short black coat.',scene='A tailored suit.')
        self.assertEqual(base,before)
        self.assertEqual(g['repair-latent']['class_type'],'VAEEncodeForInpaint')
        self.assertEqual(g['92:103']['inputs']['latent_image'],['repair-latent',0])
        self.assertEqual(g['repair-composite']['inputs']['source'],['92:104',0])
        self.assertEqual(g['repair-composite']['inputs']['destination'],['repair-base',0])
        self.assertEqual(g['76']['inputs']['image'],'source.png')
        self.assertEqual(g['81']['inputs']['image'],'design.png')


if __name__=='__main__':unittest.main()
