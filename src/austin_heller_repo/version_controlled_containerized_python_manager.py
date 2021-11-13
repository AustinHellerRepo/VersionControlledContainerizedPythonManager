from austin_heller_repo.docker_manager import DockerManager, DockerContainerInstance
from austin_heller_repo.git_manager import GitManager, GitLocalRepositoryInstance
from austin_heller_repo.threading import TimeoutThread
from typing import List, Tuple, Dict


class DockerContainerInstanceTimeoutException(Exception):

	def __init__(self, *args: object):
		super().__init__(*args)


class VersionControlledContainerizedPythonInstance():

	def __init__(self, *, timeout_thread: TimeoutThread, docker_container_instance: DockerContainerInstance, docker_manager: DockerManager):

		self.__timeout_thread = timeout_thread
		self.__docker_container_instance = docker_container_instance
		self.__docker_manager = docker_manager

	def get_output(self) -> str:
		output = self.__docker_container_instance.get_stdout()
		if output is not None:
			output = output.decode()
		return output

	def wait(self):
		is_successful = self.__timeout_thread.try_wait()
		if not is_successful:
			raise DockerContainerInstanceTimeoutException()

	def dispose(self):
		self.__docker_container_instance.stop()
		self.__docker_container_instance.remove()
		self.__docker_manager.dispose()

		self.__docker_container_instance = None
		self.__docker_manager = None

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.dispose()


class VersionControlledContainerizedPythonManager():

	def __init__(self, *, git_manager: GitManager):

		self.__git_manager = git_manager

	def run_python_script(self, *, git_repo_clone_url: str, script_file_path: str, script_arguments: List[str], timeout_seconds: float, is_docker_socket_needed: bool) -> VersionControlledContainerizedPythonInstance:

		if not self.__git_manager.is_repository_cloned_locally(
			git_url=git_repo_clone_url
		):
			git_local_repository_instance = self.__git_manager.clone(
				git_url=git_repo_clone_url
			)
		else:
			git_local_repository_instance = self.__git_manager.get_existing_local_repository_instance_from_url(
				git_url=git_repo_clone_url
			)
			if git_local_repository_instance.is_remote_commit_different(
				git_url=git_repo_clone_url
			):
				# TODO perform lock on git repo directory
				git_local_repository_instance = self.__git_manager.clone(
					git_url=git_repo_clone_url
				)

		docker_manager = DockerManager(
			dockerfile_directory_path=git_local_repository_instance.get_directory_path(),
			is_docker_socket_needed=is_docker_socket_needed
		)

		git_project_name = GitManager.get_project_name_from_git_url(
			git_url=git_repo_clone_url
		)

		docker_container_instance = docker_manager.start(
			name=f"vccpm_{git_project_name.lower()}"
		)

		concat_script_arguments = ""
		for script_argument_index, script_argument in enumerate(script_arguments):
			if script_argument_index != 0:
				concat_script_arguments += " "
			concat_script_arguments += f"{script_argument}"

		def timeout_thread_method():
			nonlocal docker_container_instance
			nonlocal script_arguments
			nonlocal script_file_path
			nonlocal concat_script_arguments

			if len(script_arguments) == 0:
				docker_container_instance.execute_command(
					command=f"python {script_file_path}"
				)
			else:
				docker_container_instance.execute_command(
					command=f"python {script_file_path} {concat_script_arguments}"
				)

			docker_container_instance.wait()

		timeout_thread = TimeoutThread(timeout_thread_method, timeout_seconds)
		timeout_thread.start()

		version_controlled_containerized_python_instance = VersionControlledContainerizedPythonInstance(
			timeout_thread=timeout_thread,
			docker_container_instance=docker_container_instance,
			docker_manager=docker_manager
		)

		return version_controlled_containerized_python_instance
