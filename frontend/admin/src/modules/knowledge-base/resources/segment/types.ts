export type SegmentListFilters = {
  page: number;
  pageSize: number;
};

export const defaultSegmentListFilters: SegmentListFilters = {
  page: 1,
  pageSize: 50,
};
