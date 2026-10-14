import unittest
from portrait_input_registry import public_catalog,identity_crop
from portrait_autorefine import dog_splits,choose_tuning_dogs


class InputRegistryTests(unittest.TestCase):
    def cohort(self):
        dogs=[dict(id=str(i),source_sha256=str(i),input=str(i)+'.png',crop=str(i)+'-face.png') for i in range(10)]
        splits=dog_splits(dogs)
        for d in dogs:d['split']=next(k for k,v in splits.items() if d['id'] in v)
        return dogs

    def test_expansion_keeps_previous_holdouts_and_groups_alternate_photos(self):
        dogs=self.cohort();before=dog_splits(dogs)
        train=next(d for d in dogs if d['split']=='train')
        dogs.extend([dict(id='new',source_sha256='new',split='train'),dict(id='alternate',source_sha256='alternate',identity_group=train['source_sha256'],split='train')])
        after=dog_splits(dogs)
        self.assertEqual(before['test'],after['test']);self.assertEqual(before['validation'],after['validation'])
        dogs[-1]['split']='test'
        with self.assertRaisesRegex(ValueError,'crosses'):dog_splits(dogs)

    def test_tuning_uses_two_clear_distinct_training_identities(self):
        dogs=self.cohort();train=dog_splits(dogs)['train']
        for d in dogs:d.update(quality_tier='challenging',quality_rank=0)
        lookup={d['id']:d for d in dogs}
        for rank,k in enumerate(train[1:4]):lookup[k].update(quality_tier='clear',quality_rank=rank)
        lookup[train[2]]['identity_group']=lookup[train[1]]['source_sha256']
        self.assertEqual(choose_tuning_dogs(lookup,train,train[0]),[train[1],train[3]])
        lookup[train[3]]['tuning_eligible']=False
        with self.assertRaises(ValueError):choose_tuning_dogs(lookup,train,train[0])

    def test_public_projection_excludes_private_metadata_and_paths(self):
        dog=dict(id='a',label='Dog',input='a.png',crop='a-face.png',source_sha256='secret',identity_group='private',quality_tier='clear')
        result=public_catalog(dict(dogs=[dog],excluded={'private':'reason'}))
        self.assertEqual(result['clear'],1);self.assertNotIn('secret',str(result));self.assertNotIn('private',str(result))
        for path in ('../secret.png','sub/secret.png','sub\\secret.png'):
            with self.assertRaises(ValueError):public_catalog({'dogs':[{**dog,'crop':path}]})

    def test_output_specific_crop_wins_without_rebinding_historical_rows(self):
        dogs=[dict(id='a',crop='old.png')]
        self.assertEqual(identity_crop({'dog_id':'a'},dogs),'old.png')
        self.assertEqual(identity_crop({'dog_id':'a','identity_crop':'new.png'},dogs),'new.png')
        self.assertEqual(identity_crop({'dog_id':'new','identity_crop':'native.png'},dogs),'native.png')
        with self.assertRaises(ValueError):identity_crop({'identity_crop':'../private.png'},dogs)


if __name__=='__main__':unittest.main()
