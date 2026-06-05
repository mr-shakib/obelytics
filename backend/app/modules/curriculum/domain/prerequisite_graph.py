from uuid import UUID


class PrerequisiteGraphValidator:
    """
    Detects cycles in the course prerequisite graph.

    adjacency_list: dict[UUID, list[UUID]] — maps course_id → list of prerequisite_course_ids
    """

    @staticmethod
    def would_create_cycle(
        adjacency: dict[UUID, list[UUID]],
        from_course: UUID,
        to_prerequisite: UUID,
    ) -> bool:
        """
        Returns True if adding edge (from_course → to_prerequisite) would create a cycle.
        Uses DFS to check if to_prerequisite can reach from_course in the existing graph.
        If it can, then adding this edge creates a cycle.
        """
        # DFS from to_prerequisite: can we reach from_course?
        visited = set()
        stack = [to_prerequisite]
        while stack:
            node = stack.pop()
            if node == from_course:
                return True
            if node in visited:
                continue
            visited.add(node)
            for neighbor in adjacency.get(node, []):
                stack.append(neighbor)
        return False
