from .generic_repo import GenericRepository


class GenericService:

    def __init__(self, repo: GenericRepository):
        self.repo = repo

    def listar(self):
        return self.repo.list_records()
    
    def get_by_id(self, id_to_search):
        return self.repo.get_by_id(id_to_search)

    def get_related_records(
        self,
        parent_id,
        relationship_name: str,
        child_relationships: tuple[str, ...] = (),
    ):
        return self.repo.get_related_records(parent_id, relationship_name, child_relationships)
    
    def create(self, data: dict):
        return self.repo.create(data)
    
    def exclude(self, id_to_delete):
        return self.repo.delete(id_to_delete)
    
    def update(self, id_to_update, **data_to_update):
        return self.repo.update(id_to_update, **data_to_update)
