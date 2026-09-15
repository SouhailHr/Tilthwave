export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ListParams {
  page?: number;
  size?: number;
  search?: string;
}

export interface EntityWithId {
  id: number | string;
}