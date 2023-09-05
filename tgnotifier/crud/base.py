from peewee import fn, JOIN

def select_with_count_of_backref(model, bmodel, alias='count', fields=None, with_zero=False):
	join = JOIN.LEFT_OUTER if with_zero else JOIN.INNER
	if fields:
		return model.select(*fields, 
			fn.COUNT(bmodel.id).alias(alias)).join(bmodel, join).group_by(*fields)
	else:
		return model.select(model.id, model.name, 
			fn.COUNT(bmodel.id).alias(alias)).join(bmodel, join).group_by(model.id, model.name)
