/** 点侧栏文件夹：当前不在其子页面时，进入第一个可见子菜单。已在子页面则只展开或收起。 */
export function folderEntry(childIds: string[], currentId: string): string | null {
  if (!childIds.length || childIds.includes(currentId)) return null
  return childIds[0]
}
