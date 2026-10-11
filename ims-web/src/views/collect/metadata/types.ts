export type FieldRow = {
  included: boolean
  fieldCode: string
  columnName: string
  displayName: string
  dataType: string
  queryConditionType: string
  dictType: string
}

export type TableColumn = {
  columnName: string
  dataType: string
  nullable: boolean
  sortOrder: number
}
