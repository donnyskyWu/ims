import { call } from "@/api/generated/endpoints";
import { BizError } from "@/api/http";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";
import { useInboxStore } from "@/stores/inbox";

const DASHBOARD = "workbench_dashboard_admin_api_ims_workbench_dashboard_get";
const TODO_PAGE = "todo_my_page_admin_api_ims_todo_my_page_get";
const TODO_COUNT = "todo_my_count_admin_api_ims_todo_my_count_get";
const TODO_COMPLETE = "todo_my_complete_admin_api_ims_todo_my_complete_post";
const TODO_OPEN = "todo_my_get_admin_api_ims_todo_my__ident__get";
const MSG_PAGE = "message_my_page_admin_api_ims_message_my_page_get";
const MSG_READ = "message_read_admin_api_ims_message_read_post";
const MSG_READ_ALL = "message_read_all_admin_api_ims_message_read_all_post";

export interface PageData<T> {
  list: T[];
  total: number;
  pageNo: number;
  pageSize: number;
}

export interface JumpInfo {
  state: string;
  path: string;
  message: string;
  delivered?: boolean;
}

export interface TodoRow {
  id: string;
  type: string;
  title: string;
  summary: string;
  status: string;
  sourceModuleLabel: string;
  route: string;
  dueTime: string | null;
  deadlineText: string;
  overdue: boolean;
  overdueDays: number;
  createTime: string | null;
  jump?: JumpInfo;
}

export interface MessageRow {
  id: string;
  title: string;
  content: string;
  summary: string;
  msgType: string;
  readStatus: string;
  route: string;
  sourceModuleLabel: string;
  createTime: string | null;
}

export interface DashboardData {
  greeting: string;
  displayName: string;
  deptName: string;
  roleSummary: string;
  todoCount: number;
  unreadMessageCount: number;
  myAccountCount: number;
  myAssetCount: number;
  myCertCount: number;
  myCertWarningCount: number;
  myLiveSessionCount: number;
  todoCountByType: Record<string, number>;
  bizCardsVisible: boolean;
}

export interface CountData {
  total: number;
  byType: Record<string, number>;
}

function queryOf(source: Record<string, unknown>): Record<string, unknown> {
  const params: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(source)) {
    if (value === undefined || value === null || value === "") continue;
    params[key] = value;
  }
  return params;
}

export function loadDashboard(): Promise<DashboardData> {
  return call<DashboardData>(DASHBOARD);
}

export function loadTodos(query: Record<string, unknown>): Promise<PageData<TodoRow>> {
  return call<PageData<TodoRow>>(TODO_PAGE, { query: queryOf(query) });
}

export function loadTodoCount(): Promise<CountData> {
  return call<CountData>(TODO_COUNT);
}

export function loadMessages(query: Record<string, unknown>): Promise<PageData<MessageRow>> {
  return call<PageData<MessageRow>>(MSG_PAGE, { query: queryOf(query) });
}

export function todoComplete(id: string): Promise<TodoRow> {
  return call<TodoRow>(TODO_COMPLETE, { body: { id } });
}

export function todoOpen(id: string): Promise<TodoRow> {
  return call<TodoRow>(TODO_OPEN, { pathParams: { ident: id }, query: { intent: "open" } });
}

export async function goHandle(id: string, push: (path: string) => void): Promise<"opened" | "closed"> {
  try {
    const data = await todoOpen(id);
    const jump = data.jump;
    if (jump?.path) push(jump.path);
    else toast.info(jump?.message || "功能将在后续批次交付");
    return "opened";
  } catch (error) {
    if (error instanceof BizError && error.code === 1297) {
      await todoComplete(id);
      return "closed";
    }
    throw error;
  }
}

export async function closeTodo(id: string): Promise<boolean> {
  try {
    await confirm({
      title: "确认关闭该待办？",
      message: "关闭后不再提醒",
      action: async () => {
        await todoComplete(id);
      },
    });
    return true;
  } catch (error) {
    if (error instanceof BizError) throw error;
    return false;
  }
}

export async function readMessages(ids: string[]): Promise<void> {
  if (!ids.length) return;
  await call(MSG_READ, { body: { ids } });
  await useInboxStore().refresh();
}

export async function readAllMessages(): Promise<number> {
  const data = await call<{ count: number }>(MSG_READ_ALL);
  await useInboxStore().refresh();
  return Number(data.count || 0);
}
