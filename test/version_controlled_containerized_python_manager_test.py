import unittest
from src.austin_heller_repo.version_controlled_containerized_python_manager import VersionControlledContainerizedPythonManager, VersionControlledContainerizedPythonInstance, DockerContainerInstanceTimeoutException
from austin_heller_repo.git_manager import GitManager
import tempfile
import docker
import time
import json


class VersionControlledContainerizedPythonManagerTest(unittest.TestCase):

	def setUp(self) -> None:

		docker_client = docker.from_env()

		image_names = [
			"vccpm_testdockertimedelay",
			"vccpm_testdockerspawnscript"
		]

		for image_name in image_names:

			try:
				docker_client.containers.get(f"{image_name}").kill()
			except Exception as ex:
				pass

			try:
				docker_client.containers.get(f"{image_name}").remove()
			except Exception as ex:
				pass

			try:
				docker_client.images.remove(
					image=f"{image_name}"
				)
			except Exception as ex:
				pass

		docker_client.close()

	def test_initialize(self):

		temp_directory = tempfile.TemporaryDirectory()

		git_manager = GitManager(
			git_directory_path=temp_directory.name
		)

		vccpm = VersionControlledContainerizedPythonManager(
			git_manager=git_manager
		)

		self.assertIsNotNone(vccpm)

		temp_directory.cleanup()

	def test_run_time_delay_script_timeout_failed(self):

		temp_directory = tempfile.TemporaryDirectory()

		git_manager = GitManager(
			git_directory_path=temp_directory.name
		)

		vccpm = VersionControlledContainerizedPythonManager(
			git_manager=git_manager
		)

		with vccpm.run_python_script(
			git_repo_clone_url="https://github.com/AustinHellerRepo/TestDockerTimeDelay.git",
			script_file_path="start.py",
			script_arguments=[],
			timeout_seconds=5,
			is_docker_socket_needed=False
		) as vccpi:
			with self.assertRaises(DockerContainerInstanceTimeoutException):
				vccpi.wait()

		temp_directory.cleanup()

	def test_run_time_delay_script(self):

		temp_directory = tempfile.TemporaryDirectory()

		git_manager = GitManager(
			git_directory_path=temp_directory.name
		)

		vccpm = VersionControlledContainerizedPythonManager(
			git_manager=git_manager
		)

		with vccpm.run_python_script(
			git_repo_clone_url="https://github.com/AustinHellerRepo/TestDockerTimeDelay.git",
			script_file_path="start.py",
			script_arguments=[],
			timeout_seconds=20,
			is_docker_socket_needed=False
		) as vccpmi:
			vccpmi.wait()
			output = vccpmi.get_output()

		self.assertEqual(b'{ "data": [ ], "exception": null }\n', output)

		temp_directory.cleanup()

	def test_run_time_delay_script_after_delay(self):

		temp_directory = tempfile.TemporaryDirectory()

		git_manager = GitManager(
			git_directory_path=temp_directory.name
		)

		vccpm = VersionControlledContainerizedPythonManager(
			git_manager=git_manager
		)

		with vccpm.run_python_script(
			git_repo_clone_url="https://github.com/AustinHellerRepo/TestDockerTimeDelay.git",
			script_file_path="start.py",
			script_arguments=[],
			timeout_seconds=5,
			is_docker_socket_needed=False
		) as vccpmi:

			time.sleep(15)

			with self.assertRaises(DockerContainerInstanceTimeoutException):
				vccpmi.wait()

		temp_directory.cleanup()

	def test_recursive_docker_spawn_script(self):

		temp_directory = tempfile.TemporaryDirectory()

		git_manager = GitManager(
			git_directory_path=temp_directory.name
		)

		vccpm = VersionControlledContainerizedPythonManager(
			git_manager=git_manager
		)

		git_url = "https://github.com/AustinHellerRepo/TestDockerTimeDelay.git"
		script_file_path = "start.py"

		with vccpm.run_python_script(
			git_repo_clone_url="https://github.com/AustinHellerRepo/TestDockerSpawnScript.git",
			script_file_path="/app/start.py",
			script_arguments=["-g", git_url, "-s", script_file_path, "-t", "20"],
			timeout_seconds=30,
			is_docker_socket_needed=True
		) as vccpi:
			vccpi.wait()
			output = vccpi.get_output()

		temp_directory.cleanup()

		print(f"output: {output}")

		output_json = json.loads(output.decode())

		self.assertEqual(0, len(output_json["data"][0]))
		self.assertEqual(git_url, output_json["data"][1])
		self.assertEqual(script_file_path, output_json["data"][2])

		print(f"Execution time: {output_json['data'][4]}")
