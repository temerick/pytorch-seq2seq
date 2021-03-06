from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import spacy

import os
import re
from dataloaders.text.torchtext import data
from dataloaders.text.torchtext import datasets
import glob

url = re.compile('(<url>.*</url>)')

seg = re.compile(r'<seg id="\d+">(.+)</seg>')

def fix_xml(fn):
    target_fn = fn[:-4] # Take away ".xml"
    new = []
    with open(fn, 'r') as f:
        for l in f.read().splitlines():
            match = seg.search(l)
            if match:
                new.append(match.group(0))
    with open(target_fn, 'w') as f:
        for l in new:
            f.write(l + '\n')


def tokenize(text, spacy_inst):
    return [tok.text for tok in spacy_inst.tokenizer(url.sub('@URL@', text))]


def make_dataset(path='dataloaders/iwslt2016/'):
    if not os.path.exists(path):
        print("Downloading dataset")
        os.system('wget https://wit3.fbk.eu/archive/2016-01//texts/de/en/de-en.tgz')
        os.system('tar -xvzf de-en.tgz -C {}'.format(path))
        for fn in glob.glob(path + "*.xml"):
            fix_xml(fn)

    spacy_de = spacy.load('de')
    spacy_en = spacy.load('en')

    DE = data.Field(tokenize=lambda x: tokenize(x, spacy_de))
    EN = data.Field(tokenize=lambda x: tokenize(x, spacy_en), init_token='<bos>', eos_token='<eos>')

    train, val = datasets.TranslationDataset.splits(
        path=path, train='train.tags.de-en',
        validation='IWSLT16.TED.tst2013.de-en', exts=('.de', '.en'),
        fields=(DE, EN))

    DE.build_vocab(train.src, min_freq=10)
    EN.build_vocab(train.trg, max_size=50000)
    n_ex = len(train.examples)
    train.examples = [x for x in train.examples if len(x.src) < 40] # These are garbage
    print("Number of examples {} -> {}".format(n_ex, len(train.examples)))
    return train, val, DE, EN


def loader(batch_size=32):
    """
    Loader for the translation task. Loading text is really fast, so we wont parallelize this
    :param batch_size:
    :return:
    """
    train, val, de, en = make_dataset()
    train_iter = data.BucketIterator(dataset=train, batch_size=batch_size, repeat=False, sort=True)
    
    #val_iter = data.BucketIterator(dataset=val, batch_size=batch_size, train=False, repeat=False, sort=True)
    val_iter = data.Iterator(dataset=val, batch_size=batch_size, train=False, repeat=False, shuffle=True)

    return de, en, train_iter, val_iter
