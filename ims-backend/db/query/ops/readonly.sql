-- name: ListLiveRoom :many
SELECT id, author_id, status FROM live_room WHERE author_id = ? LIMIT ?;
