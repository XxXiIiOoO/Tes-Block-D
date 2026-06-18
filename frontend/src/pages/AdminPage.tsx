import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import {
  createAdminUser,
  createProjectMember,
  deleteAdminUser,
  deleteProjectMember,
  getAdminUsers,
  getAuditEvents,
  getProjectMembers,
  getProjects,
  updateAdminUser,
  updateProjectMember,
} from "../api/blocktest";
import { useAuth } from "../auth/AuthContext";
import { PageState } from "../components/PageState";
import { useAppPreferences } from "../preferences/AppPreferencesContext";
import type { AdminUserCreatePayload, AdminUserUpdatePayload, AuditEvent, Project, ProjectMember, User } from "../types";
import { formatDate, toErrorMessage } from "../utils";

const roleOptions: Array<User["role"]> = ["admin", "worker", "viewer"];
const projectRoleOptions: Array<ProjectMember["role"]> = ["developer", "viewer"];

type UserDraft = {
  email: string;
  username: string;
  password: string;
  role: User["role"];
  full_name: string;
  position: string;
  avatar_url: string;
  bio: string;
};

function roleLabel(role: User["role"], t: (key: string) => string) {
  return t(`admin.role.${role}`);
}

function projectRoleLabel(role: ProjectMember["role"], t: (key: string) => string) {
  return t(`admin.projectRole.${role}`);
}

function userToDraft(currentUser: User): UserDraft {
  return {
    email: currentUser.email,
    username: currentUser.username,
    password: "",
    role: currentUser.role,
    full_name: currentUser.full_name ?? "",
    position: currentUser.position ?? "",
    avatar_url: currentUser.avatar_url ?? "",
    bio: currentUser.bio ?? "",
  };
}

function emptyCreateDraft(): AdminUserCreatePayload {
  return {
    email: "",
    username: "",
    password: "",
    role: "worker",
    email_verified: true,
    full_name: "",
    position: "",
    avatar_url: "",
    bio: "",
  };
}

function compactOptional(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function buildUpdatePayload(draft: UserDraft, currentUser: User): AdminUserUpdatePayload {
  const payload: AdminUserUpdatePayload = {};
  if (draft.email.trim() !== currentUser.email) {
    payload.email = draft.email.trim();
  }
  if (draft.username.trim() !== currentUser.username) {
    payload.username = draft.username.trim();
  }
  if (draft.password.trim()) {
    payload.password = draft.password;
  }
  if (draft.role !== currentUser.role) {
    payload.role = draft.role;
  }
  if (compactOptional(draft.full_name) !== currentUser.full_name) {
    payload.full_name = compactOptional(draft.full_name);
  }
  if (compactOptional(draft.position) !== currentUser.position) {
    payload.position = compactOptional(draft.position);
  }
  if (compactOptional(draft.avatar_url) !== currentUser.avatar_url) {
    payload.avatar_url = compactOptional(draft.avatar_url);
  }
  if (compactOptional(draft.bio) !== currentUser.bio) {
    payload.bio = compactOptional(draft.bio);
  }
  return payload;
}

export function AdminPage() {
  const { user } = useAuth();
  const { t } = useAppPreferences();
  const [users, setUsers] = useState<User[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectMembers, setProjectMembers] = useState<ProjectMember[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<"all" | User["role"]>("all");
  const [drafts, setDrafts] = useState<Record<number, UserDraft>>({});
  const [createDraft, setCreateDraft] = useState<AdminUserCreatePayload>(() => emptyCreateDraft());
  const [assignmentDraft, setAssignmentDraft] = useState<{
    userId: string;
    projectId: string;
    role: ProjectMember["role"];
  }>({ userId: "", projectId: "", role: "viewer" });
  const [loading, setLoading] = useState(true);
  const [savingUserId, setSavingUserId] = useState<number | "create" | "assignment" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canViewPage = Boolean(user?.is_admin);

  async function loadData(silent = false) {
    if (!silent) {
      setLoading(true);
    }
    setError(null);

    try {
      const [usersResponse, eventsResponse, projectsResponse] = await Promise.all([
        getAdminUsers({
          search: search.trim() || undefined,
          role: roleFilter === "all" ? undefined : roleFilter,
        }),
        getAuditEvents({ limit: 150 }),
        getProjects(),
      ]);
      const projectMembersResponse = (
        await Promise.all(projectsResponse.map((project) => getProjectMembers(project.id).catch(() => [])))
      ).flat();
      setUsers(usersResponse);
      setProjects(projectsResponse);
      setProjectMembers(projectMembersResponse);
      setAuditEvents(eventsResponse);
      setDrafts(Object.fromEntries(usersResponse.map((currentUser) => [currentUser.id, userToDraft(currentUser)])));
    } catch (loadError) {
      setError(toErrorMessage(loadError, t("admin.loadError")));
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    if (!canViewPage) {
      setLoading(false);
      return;
    }
    void loadData();
  }, [canViewPage, roleFilter]);

  const filteredUsers = useMemo(() => {
    const normalized = search.trim().toLowerCase();
    if (!normalized) {
      return users;
    }
    return users.filter((currentUser) => {
      const fields = [
        currentUser.email,
        currentUser.username,
        currentUser.full_name ?? "",
        currentUser.position ?? "",
      ];
      return fields.some((value) => value.toLowerCase().includes(normalized));
    });
  }, [search, users]);

  const pendingUsers = useMemo(() => users.filter((currentUser) => !currentUser.email_verified), [users]);

  function updateDraft(userId: number, patch: Partial<UserDraft>) {
    setDrafts((prev) => ({
      ...prev,
      [userId]: {
        ...prev[userId],
        ...patch,
      },
    }));
  }

  async function handleCreateUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSavingUserId("create");
    setError(null);
    try {
      const created = await createAdminUser({
        ...createDraft,
        email: createDraft.email.trim(),
        username: createDraft.username.trim(),
        full_name: compactOptional(createDraft.full_name ?? ""),
        position: compactOptional(createDraft.position ?? ""),
        avatar_url: compactOptional(createDraft.avatar_url ?? ""),
        bio: compactOptional(createDraft.bio ?? ""),
      });
      setUsers((prev) => [created, ...prev]);
      setDrafts((prev) => ({ ...prev, [created.id]: userToDraft(created) }));
      setCreateDraft(emptyCreateDraft());
      await loadData(true);
    } catch (createError) {
      setError(toErrorMessage(createError, t("admin.createUserError")));
    } finally {
      setSavingUserId(null);
    }
  }

  async function handleSaveUser(currentUser: User) {
    const draft = drafts[currentUser.id] ?? userToDraft(currentUser);
    const payload = buildUpdatePayload(draft, currentUser);
    if (Object.keys(payload).length === 0) {
      return;
    }

    setSavingUserId(currentUser.id);
    setError(null);
    try {
      const updated = await updateAdminUser(currentUser.id, payload);
      setUsers((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
      setDrafts((prev) => ({ ...prev, [updated.id]: userToDraft(updated) }));
      await loadData(true);
    } catch (saveError) {
      setError(toErrorMessage(saveError, t("admin.saveUserError")));
    } finally {
      setSavingUserId(null);
    }
  }

  async function handleSetEmailVerification(currentUser: User, emailVerified: boolean) {
    setSavingUserId(currentUser.id);
    setError(null);
    try {
      const updated = await updateAdminUser(currentUser.id, { email_verified: emailVerified });
      setUsers((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
      setDrafts((prev) => ({ ...prev, [updated.id]: userToDraft(updated) }));
      await loadData(true);
    } catch (saveError) {
      setError(toErrorMessage(saveError, t("admin.emailStatusError")));
    } finally {
      setSavingUserId(null);
    }
  }

  async function handleDeleteUser(currentUser: User) {
    const confirmed = window.confirm(t("admin.deleteUserConfirm", { email: currentUser.email }));
    if (!confirmed) {
      return;
    }

    setSavingUserId(currentUser.id);
    setError(null);
    try {
      await deleteAdminUser(currentUser.id);
      setUsers((prev) => prev.filter((item) => item.id !== currentUser.id));
      setDrafts((prev) => {
        const next = { ...prev };
        delete next[currentUser.id];
        return next;
      });
      await loadData(true);
    } catch (deleteError) {
      setError(toErrorMessage(deleteError, t("admin.deleteUserError")));
    } finally {
      setSavingUserId(null);
    }
  }

  async function handleAssignProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const userId = Number(assignmentDraft.userId);
    const projectId = Number(assignmentDraft.projectId);
    if (!Number.isFinite(userId) || !Number.isFinite(projectId)) {
      return;
    }

    setSavingUserId("assignment");
    setError(null);
    try {
      const created = await createProjectMember(projectId, {
        user_id: userId,
        role: assignmentDraft.role,
      });
      setProjectMembers((prev) => [created, ...prev]);
      setAssignmentDraft((prev) => ({ ...prev, userId: "", projectId: "" }));
      await loadData(true);
    } catch (assignError) {
      setError(toErrorMessage(assignError, t("admin.assignProjectError")));
    } finally {
      setSavingUserId(null);
    }
  }

  async function handleUpdateProjectMember(member: ProjectMember, role: ProjectMember["role"]) {
    setSavingUserId("assignment");
    setError(null);
    try {
      const updated = await updateProjectMember(member.project_id, member.id, { role });
      setProjectMembers((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
      await loadData(true);
    } catch (updateError) {
      setError(toErrorMessage(updateError, t("admin.updateProjectRoleError")));
    } finally {
      setSavingUserId(null);
    }
  }

  async function handleDeleteProjectMember(member: ProjectMember) {
    const project = projects.find((item) => item.id === member.project_id);
    const confirmed = window.confirm(
      t("admin.removeProjectAccessConfirm", {
        email: member.email,
        project: project?.name ?? String(member.project_id),
      }),
    );
    if (!confirmed) {
      return;
    }

    setSavingUserId("assignment");
    setError(null);
    try {
      await deleteProjectMember(member.project_id, member.id);
      setProjectMembers((prev) => prev.filter((item) => item.id !== member.id));
      await loadData(true);
    } catch (deleteError) {
      setError(toErrorMessage(deleteError, t("admin.removeProjectAccessError")));
    } finally {
      setSavingUserId(null);
    }
  }

  if (!canViewPage) {
    return (
      <div className="page-stack">
        <section className="section-card">
          <h1>{t("admin.deniedTitle")}</h1>
          <p className="muted">{t("admin.deniedText")}</p>
        </section>
      </div>
    );
  }

  const state = (
    <PageState
      loading={loading}
      error={error && users.length === 0 ? error : null}
      emptyMessage={t("admin.emptyUsers")}
      hasData={users.length > 0}
    />
  );

  return (
    <div className="page-stack">
      <section className="hero-card hero-card-compact">
        <div>
          <p className="eyebrow">{t("admin.eyebrow")}</p>
          <h1>{t("admin.title")}</h1>
          <p className="muted">{t("admin.subtitle")}</p>
        </div>
        <div className="toolbar">
          <label className="field field-inline">
            <span>{t("admin.role")}</span>
            <select
              value={roleFilter}
              onChange={(event) => setRoleFilter(event.target.value as "all" | User["role"])}
            >
              <option value="all">{t("admin.allRoles")}</option>
              {roleOptions.map((role) => (
                <option key={role} value={role}>
                  {roleLabel(role, t)}
                </option>
              ))}
            </select>
          </label>
          <button className="button button-ghost" type="button" onClick={() => void loadData()}>
            {t("common.refresh")}
          </button>
        </div>
      </section>

      <section className="section-card">
        <div className="card-header">
          <div>
            <p className="eyebrow">{t("admin.registrationRequestsEyebrow")}</p>
            <h2>{t("admin.registrationRequestsTitle")}</h2>
            <p className="muted">{t("admin.registrationRequestsSubtitle")}</p>
          </div>
          <span className="counter-chip">{pendingUsers.length}</span>
        </div>

        {pendingUsers.length > 0 ? (
          <div className="list-grid">
            {pendingUsers.map((pendingUser) => (
              <article className="list-card" key={pendingUser.id}>
                <div className="list-card-top">
                  <div>
                    <p className="eyebrow">#{pendingUser.id}</p>
                    <h3>{pendingUser.full_name?.trim() || pendingUser.username}</h3>
                  </div>
                  <span className="code-chip">{pendingUser.email}</span>
                </div>
                <p className="muted">
                  {t("admin.registrationRequestMeta", {
                    role: roleLabel(pendingUser.role, t),
                    created: formatDate(pendingUser.created_at),
                  })}
                </p>
                <div className="actions-row">
                  <button
                    className="button button-primary"
                    type="button"
                    disabled={savingUserId === pendingUser.id}
                    onClick={() => void handleSetEmailVerification(pendingUser, true)}
                  >
                    {t("admin.approveRegistration")}
                  </button>
                  <button
                    className="button button-danger"
                    type="button"
                    disabled={savingUserId === pendingUser.id}
                    onClick={() => void handleDeleteUser(pendingUser)}
                  >
                    {t("common.delete")}
                  </button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <PageState emptyMessage={t("admin.emptyRegistrationRequests")} hasData={false} />
        )}
      </section>

      <section className="section-card">
        <div className="card-header">
          <div>
            <p className="eyebrow">{t("admin.projectAclEyebrow")}</p>
            <h2>{t("admin.assignProjectTitle")}</h2>
            <p className="muted">{t("admin.assignProjectSubtitle")}</p>
          </div>
          <span className="counter-chip">{projectMembers.length}</span>
        </div>

        <form className="admin-user-form" onSubmit={handleAssignProject}>
          <label className="field">
            <span>{t("admin.user")}</span>
            <select
              value={assignmentDraft.userId}
              onChange={(event) => setAssignmentDraft((prev) => ({ ...prev, userId: event.target.value }))}
              required
            >
              <option value="">{t("admin.selectUser")}</option>
              {users.map((currentUser) => (
                <option key={currentUser.id} value={currentUser.id}>
                  {currentUser.email} · {currentUser.username}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>{t("admin.project")}</span>
            <select
              value={assignmentDraft.projectId}
              onChange={(event) => setAssignmentDraft((prev) => ({ ...prev, projectId: event.target.value }))}
              required
            >
              <option value="">{t("admin.selectProject")}</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name} · #{project.id}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>{t("admin.projectRole")}</span>
            <select
              value={assignmentDraft.role}
              onChange={(event) =>
                setAssignmentDraft((prev) => ({ ...prev, role: event.target.value as ProjectMember["role"] }))
              }
            >
              {projectRoleOptions.map((role) => (
                <option key={role} value={role}>
                  {projectRoleLabel(role, t)}
                </option>
              ))}
            </select>
          </label>
          <div className="actions-row">
            <button className="button button-primary" disabled={savingUserId === "assignment"} type="submit">
              {t("admin.assign")}
            </button>
          </div>
        </form>

        {projectMembers.length > 0 ? (
          <div className="list-grid admin-assignments-grid">
            {projectMembers.map((member) => {
              const project = projects.find((item) => item.id === member.project_id);
              return (
                <article className="list-card" key={member.id}>
                  <div className="list-card-top">
                    <div>
                      <p className="eyebrow">#{member.id}</p>
                      <h3>{project?.name ?? `Project #${member.project_id}`}</h3>
                    </div>
                    <span className="code-chip">{member.email}</span>
                  </div>
                  <div className="meta-row">
                    <span>{member.full_name?.trim() || member.username}</span>
                    <span>{projectRoleLabel(member.role, t)}</span>
                    <span>{formatDate(member.created_at)}</span>
                  </div>
                  <div className="actions-row">
                    <select
                      value={member.role}
                      disabled={savingUserId === "assignment"}
                      onChange={(event) =>
                        void handleUpdateProjectMember(member, event.target.value as ProjectMember["role"])
                      }
                    >
                      {projectRoleOptions.map((role) => (
                        <option key={role} value={role}>
                          {projectRoleLabel(role, t)}
                        </option>
                      ))}
                    </select>
                    <button
                      className="button button-danger"
                      type="button"
                      disabled={savingUserId === "assignment"}
                      onClick={() => void handleDeleteProjectMember(member)}
                    >
                      {t("admin.removeAccess")}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <PageState emptyMessage={t("admin.emptyAssignments")} hasData={false} />
        )}
      </section>

      <section className="section-card">
        <div className="card-header">
          <div>
            <p className="eyebrow">{t("admin.createUserEyebrow")}</p>
            <h2>{t("admin.createUserTitle")}</h2>
          </div>
        </div>
        <form className="admin-user-form" onSubmit={handleCreateUser}>
          <label className="field">
            <span>{t("common.email")}</span>
            <input
              type="email"
              value={createDraft.email}
              onChange={(event) => setCreateDraft((prev) => ({ ...prev, email: event.target.value }))}
              required
            />
          </label>
          <label className="field">
            <span>{t("admin.username")}</span>
            <input
              value={createDraft.username}
              onChange={(event) => setCreateDraft((prev) => ({ ...prev, username: event.target.value }))}
              required
              minLength={3}
            />
          </label>
          <label className="field">
            <span>{t("admin.password")}</span>
            <input
              type="password"
              value={createDraft.password}
              onChange={(event) => setCreateDraft((prev) => ({ ...prev, password: event.target.value }))}
              required
              minLength={8}
            />
          </label>
          <label className="field">
            <span>{t("admin.role")}</span>
            <select
              value={createDraft.role}
              onChange={(event) =>
                setCreateDraft((prev) => ({ ...prev, role: event.target.value as User["role"] }))
              }
            >
              {roleOptions.map((role) => (
                <option key={role} value={role}>
                  {roleLabel(role, t)}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>{t("admin.fullName")}</span>
            <input
              value={createDraft.full_name ?? ""}
              onChange={(event) => setCreateDraft((prev) => ({ ...prev, full_name: event.target.value }))}
            />
          </label>
          <label className="field">
            <span>{t("admin.position")}</span>
            <input
              value={createDraft.position ?? ""}
              onChange={(event) => setCreateDraft((prev) => ({ ...prev, position: event.target.value }))}
            />
          </label>
          <div className="actions-row">
            <button className="button button-primary" disabled={savingUserId === "create"} type="submit">
              {t("common.create")}
            </button>
          </div>
        </form>
      </section>

      <section className="section-card">
        <div className="card-header">
          <div>
            <p className="eyebrow">{t("admin.users")}</p>
            <h2>{t("admin.editUsersTitle")}</h2>
          </div>
          <span className="counter-chip">{filteredUsers.length}</span>
        </div>

        <label className="field">
          <span>{t("common.search")}</span>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t("admin.searchPlaceholder")}
          />
        </label>

        {loading && users.length === 0 ? state : null}
        {error && users.length > 0 ? <div className="state-card state-card-error">{error}</div> : null}

        {filteredUsers.length > 0 ? (
          <div className="list-grid admin-users-grid">
            {filteredUsers.map((currentUser) => {
              const draft = drafts[currentUser.id] ?? userToDraft(currentUser);
              return (
                <article className="list-card" key={currentUser.id}>
                  <div className="list-card-top">
                    <div>
                      <p className="eyebrow">#{currentUser.id}</p>
                      <h3>{currentUser.full_name?.trim() || currentUser.username}</h3>
                    </div>
                    <span className="code-chip">{currentUser.email}</span>
                  </div>
                  <p className="muted">
                    {currentUser.position?.trim() || t("admin.positionEmpty")} · {roleLabel(currentUser.role, t)}
                  </p>
                  <div className="admin-user-form">
                    <label className="field">
                      <span>{t("common.email")}</span>
                      <input
                        type="email"
                        value={draft.email}
                        onChange={(event) => updateDraft(currentUser.id, { email: event.target.value })}
                      />
                    </label>
                    <label className="field">
                      <span>{t("admin.username")}</span>
                      <input
                        value={draft.username}
                        onChange={(event) => updateDraft(currentUser.id, { username: event.target.value })}
                      />
                    </label>
                    <label className="field">
                      <span>{t("admin.newPassword")}</span>
                      <input
                        type="password"
                        value={draft.password}
                        placeholder={t("admin.passwordUnchangedPlaceholder")}
                        onChange={(event) => updateDraft(currentUser.id, { password: event.target.value })}
                      />
                    </label>
                    <label className="field">
                      <span>{t("admin.role")}</span>
                      <select
                        value={draft.role}
                        onChange={(event) => updateDraft(currentUser.id, { role: event.target.value as User["role"] })}
                      >
                        {roleOptions.map((role) => (
                          <option key={role} value={role}>
                            {roleLabel(role, t)}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field">
                      <span>{t("admin.fullName")}</span>
                      <input
                        value={draft.full_name}
                        onChange={(event) => updateDraft(currentUser.id, { full_name: event.target.value })}
                      />
                    </label>
                    <label className="field">
                      <span>{t("admin.position")}</span>
                      <input
                        value={draft.position}
                        onChange={(event) => updateDraft(currentUser.id, { position: event.target.value })}
                      />
                    </label>
                    <label className="field">
                      <span>Avatar URL</span>
                      <input
                        value={draft.avatar_url}
                        onChange={(event) => updateDraft(currentUser.id, { avatar_url: event.target.value })}
                      />
                    </label>
                    <label className="field admin-user-bio">
                      <span>Bio</span>
                      <textarea
                        rows={3}
                        value={draft.bio}
                        onChange={(event) => updateDraft(currentUser.id, { bio: event.target.value })}
                      />
                    </label>
                  </div>
                  <div className="meta-row">
                    <span>{t("admin.email")}: {currentUser.email_verified ? t("admin.emailVerified") : t("admin.emailNotVerified")}</span>
                    <span>{t("common.created")}: {formatDate(currentUser.created_at)}</span>
                  </div>
                  <div className="actions-row">
                    <button
                      className="button button-primary"
                      type="button"
                      disabled={savingUserId === currentUser.id}
                      onClick={() => void handleSaveUser(currentUser)}
                    >
                      {t("common.save")}
                    </button>
                    <button
                      className={currentUser.email_verified ? "button button-ghost" : "button button-primary"}
                      type="button"
                      disabled={savingUserId === currentUser.id}
                      onClick={() => void handleSetEmailVerification(currentUser, !currentUser.email_verified)}
                    >
                      {currentUser.email_verified ? t("admin.resetVerification") : t("admin.approveRegistration")}
                    </button>
                    <button
                      className="button button-ghost"
                      type="button"
                      disabled={savingUserId === currentUser.id}
                      onClick={() => setDrafts((prev) => ({ ...prev, [currentUser.id]: userToDraft(currentUser) }))}
                    >
                      {t("common.reset")}
                    </button>
                    <button
                      className="button button-danger"
                      type="button"
                      disabled={savingUserId === currentUser.id}
                      onClick={() => void handleDeleteUser(currentUser)}
                    >
                      {t("common.delete")}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        ) : null}
      </section>

      <section className="section-card">
        <div className="card-header">
          <div>
            <p className="eyebrow">{t("admin.audit")}</p>
            <h2>{t("admin.latestEvents")}</h2>
          </div>
          <span className="counter-chip">{auditEvents.length}</span>
        </div>

        {auditEvents.length === 0 ? (
          <PageState emptyMessage={t("admin.emptyAudit")} hasData={false} />
        ) : (
          <div className="list-grid">
            {auditEvents.map((event) => (
              <article className="list-card" key={event.id}>
                <div className="list-card-top">
                  <div>
                    <p className="eyebrow">{event.action}</p>
                    <h3>{event.username ?? "system"}</h3>
                  </div>
                  <span className="counter-chip">#{event.id}</span>
                </div>
                <p className="muted">
                  {event.entity_type ?? "entity"}:{event.entity_id ?? "—"}
                </p>
                <p>{event.details ?? t("admin.detailsEmpty")}</p>
                <div className="meta-row">
                  <span>{formatDate(event.created_at)}</span>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
